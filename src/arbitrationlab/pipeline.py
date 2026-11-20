"""Pipeline ponta a ponta: candidatos -> normalizacao -> evidencia -> calibracao -> decisao.

Um unico `max_spend` cobre candidatos, verificacoes e o juiz. O juiz e consultivo: a sua
sugestao fica registada, mas nunca altera a decisao de um campo.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from arbitrationlab.calibration import ConfidenceModel, ReliabilityTable
from arbitrationlab.decision import (
    FieldAssessment,
    Policy,
    apply_verification,
    assess_field,
    detect_injection_lines,
)
from arbitrationlab.generation.providers import CandidateProvider
from arbitrationlab.generation.runner import BudgetLedger, CandidateRecord, generate_candidates
from arbitrationlab.schema import field_specs, validate_output_schema


@dataclass(frozen=True)
class Outcome:
    verdicts: dict[str, FieldAssessment]
    candidates: tuple[CandidateRecord, ...]
    spent_usd: float
    suspected_injection: bool
    latency_ms: float
    judge_suggestion: dict[str, Any] | None = None
    notes: list[str] = field(default_factory=list)

    def accepted_values(self) -> dict[str, Any]:
        return {name: v.accepted_value for name, v in self.verdicts.items()}


def select_candidates(
    providers: Sequence[CandidateProvider], names: tuple[str, ...] | None
) -> list[CandidateProvider]:
    """Escolhe os candidatos por nome, pela ordem pedida. Nome desconhecido e erro."""
    if names is None:
        return list(providers)
    by_name = {p.name: p for p in providers}
    unknown = [n for n in names if n not in by_name]
    if unknown:
        raise ValueError(f"candidatos desconhecidos: {', '.join(unknown)}")
    return [by_name[n] for n in names]


async def _call_with_timeout(
    provider: CandidateProvider, text: str, schema: dict[str, Any], timeout_s: float
) -> dict[str, Any] | None:
    try:
        output = await asyncio.wait_for(provider.extract(text, schema), timeout=timeout_s)
    except Exception:  # noqa: BLE001 - falha do verificador/juiz nunca derruba a arbitragem
        return None
    return output if isinstance(output, dict) else None


async def arbitrate(
    text: str,
    schema: dict[str, Any],
    providers: Sequence[CandidateProvider],
    *,
    policy: Policy,
    reliability: ReliabilityTable | None = None,
    calibrator: ConfidenceModel | None = None,
    verifier: CandidateProvider | None = None,
    judge: CandidateProvider | None = None,
) -> Outcome:
    """Arbitra os campos de `schema` sobre `text`. Lanca ValueError para entradas invalidas."""
    if not isinstance(text, str):
        raise ValueError("o texto tem de ser uma string")
    validate_output_schema(schema)
    started = time.perf_counter()
    reliability = reliability or ReliabilityTable()
    calibrator = calibrator or ConfidenceModel()
    ledger = BudgetLedger(policy.max_spend)
    selected = select_candidates(providers, policy.candidates)
    records = await generate_candidates(
        text, schema, selected, timeout_s=policy.timeout_s, ledger=ledger
    )
    tainted = detect_injection_lines(text)
    verdicts: dict[str, FieldAssessment] = {}
    for name, spec in field_specs(schema).items():
        raw_by_model = [(r.model, r.status, (r.output or {}).get(name)) for r in records]
        assessment = assess_field(
            name,
            spec["x-type"],
            spec["x-label"],
            text,
            raw_by_model,
            reliability=reliability,
            calibrator=calibrator,
            policy=policy,
            tainted_lines=tainted,
        )
        if assessment.decision == "verify":
            assessment = await _verify_field(
                assessment, name, spec, text, schema, verifier, ledger, policy, tainted
            )
        verdicts[name] = assessment
    suggestion = await _judge_suggestion(text, schema, judge, ledger, policy, verdicts)
    return Outcome(
        verdicts=verdicts,
        candidates=tuple(records),
        spent_usd=round(ledger.spent, 10),
        suspected_injection=bool(tainted),
        latency_ms=(time.perf_counter() - started) * 1000,
        judge_suggestion=suggestion,
    )


async def _verify_field(
    assessment: FieldAssessment,
    name: str,
    spec: dict[str, str],
    text: str,
    schema: dict[str, Any],
    verifier: CandidateProvider | None,
    ledger: BudgetLedger,
    policy: Policy,
    tainted: frozenset[int],
) -> FieldAssessment:
    common = {
        "field_type": spec["x-type"],
        "label": spec["x-label"],
        "text": text,
        "tainted_lines": tainted,
    }
    if verifier is None:
        return apply_verification(
            assessment, verified_raw=None, skipped_reason="no_verifier", **common
        )
    if not ledger.try_reserve(verifier.cost_per_call_usd):
        return apply_verification(
            assessment, verified_raw=None, skipped_reason="skipped: budget", **common
        )
    output = await _call_with_timeout(verifier, text, schema, policy.timeout_s)
    raw = None if output is None else output.get(name)
    return apply_verification(assessment, verified_raw=raw, **common)


async def _judge_suggestion(
    text: str,
    schema: dict[str, Any],
    judge: CandidateProvider | None,
    ledger: BudgetLedger,
    policy: Policy,
    verdicts: dict[str, FieldAssessment],
) -> dict[str, Any] | None:
    if not policy.judge or judge is None:
        return None
    if not ledger.try_reserve(judge.cost_per_call_usd):
        return {"model": judge.name, "advisory": True, "status": "skipped: budget"}
    output = await _call_with_timeout(judge, text, schema, policy.timeout_s)
    if output is None:
        return {"model": judge.name, "advisory": True, "status": "failed"}
    disagreements = [
        name
        for name, verdict in verdicts.items()
        if name in output
        and verdict.accepted_value is not None
        and output[name] != verdict.accepted_value
    ]
    return {
        "model": judge.name,
        "advisory": True,
        "status": "ok",
        "values": output,
        "disagrees_with_accepted": disagreements,
    }


def arbitrate_sync(
    text: str,
    schema: dict[str, Any],
    providers: Sequence[CandidateProvider],
    **kwargs: Any,
) -> Outcome:
    """Versao sincrona para a API e para as experiencias. Nao chamar dentro de um loop asyncio."""
    return asyncio.run(arbitrate(text, schema, providers, **kwargs))
