"""As cinco estrategias comparadas sobre o mesmo split de avaliacao.

1. cheap_single: um modelo barato, sem arbitragem.
2. strong_single: um modelo forte, sem arbitragem.
3. majority_vote: voto maioritario entre os tres candidatos, sem evidencia.
4. evidence_arbitration: arbitragem por evidencia; campos em revisao ficam sem valor.
5. arbitration_review: arbitragem + revisao humana simulada a partir dos labels.
"""

from __future__ import annotations

import asyncio
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from arbitrationlab.calibration import ConfidenceModel, ReliabilityTable
from arbitrationlab.decision import Policy
from arbitrationlab.generation.providers import CandidateProvider
from arbitrationlab.generation.registry import CHEAP_A, CHEAP_B, STRONG_C, VERIFIER
from arbitrationlab.generation.runner import generate_candidates
from arbitrationlab.normalize import normalize
from arbitrationlab.pipeline import arbitrate_sync
from arbitrationlab.schema import claim_output_schema, field_specs

STRATEGIES: tuple[str, ...] = (
    "cheap_single",
    "strong_single",
    "majority_vote",
    "evidence_arbitration",
    "arbitration_review",
)
LABELS = {
    "cheap_single": "modelo barato único",
    "strong_single": "modelo forte único",
    "majority_vote": "voto maioritário",
    "evidence_arbitration": "arbitragem por evidência",
    "arbitration_review": "arbitragem + revisão",
}
REVIEWABLE = frozenset({"human_review", "abstain"})
MAX_SPEND = 0.05
TIMEOUT_S = 5.0
AMOUNT_TOLERANCE = 0.005


@dataclass(frozen=True)
class CaseResult:
    strategy: str
    case_id: str
    difficulty: str
    final: dict[str, Any]
    gold: dict[str, Any]
    model_cost: float
    review_cost: float
    n_reviewed: int
    latency_ms: float
    decisions: dict[str, str] = field(default_factory=dict)
    candidate_values: dict[str, dict[str, Any]] = field(default_factory=dict)


def same_value(field_type: str, left: Any, right: Any) -> bool:
    """Igualdade de valores canonicos. Ausente (None) so e igual a ausente."""
    if left is None or right is None:
        return left is None and right is None
    if field_type == "amount":
        return abs(float(left) - float(right)) < AMOUNT_TOLERANCE
    return left == right


def normalized_output(output: dict[str, Any] | None) -> dict[str, Any]:
    """Valor canonico de cada campo de um candidato (None se ausente ou nao normalizavel)."""
    specs = field_specs(claim_output_schema())
    result: dict[str, Any] = {}
    for name, spec in specs.items():
        raw = (output or {}).get(name)
        norm = normalize(spec["x-type"], raw)
        result[name] = norm.value if norm.ok else None
    return result


def _candidate_records(text: str, providers: list[CandidateProvider]) -> list[Any]:
    return asyncio.run(
        generate_candidates(
            text, claim_output_schema(), providers, max_spend=MAX_SPEND, timeout_s=TIMEOUT_S
        )
    )


def _majority(records: list[Any]) -> dict[str, Any]:
    final: dict[str, Any] = {}
    specs = field_specs(claim_output_schema())
    for name in specs:
        values = [normalized_output(r.output)[name] for r in records if r.usable]
        present = [v for v in values if v is not None]
        final[name] = Counter(present).most_common(1)[0][0] if present else None
    return final


def _single(
    strategy: str,
    case: dict[str, Any],
    providers: list[CandidateProvider],
) -> CaseResult:
    started = time.perf_counter()
    records = _candidate_records(case["text"], providers)
    latency = (time.perf_counter() - started) * 1000
    if strategy == "majority_vote":
        final = _majority(records)
    else:
        final = normalized_output(records[0].output if records[0].usable else None)
    return CaseResult(
        strategy=strategy,
        case_id=case["id"],
        difficulty=case["difficulty"],
        final=final,
        gold=case["gold"],
        model_cost=sum(r.cost_usd for r in records),
        review_cost=0.0,
        n_reviewed=0,
        latency_ms=latency,
        candidate_values={r.model: normalized_output(r.output) for r in records if r.usable},
    )


def _arbitration(
    strategy: str,
    case: dict[str, Any],
    models: dict[str, CandidateProvider],
    reliability: ReliabilityTable,
    calibrator: ConfidenceModel,
    review_cost_usd: float,
) -> CaseResult:
    providers = [models[CHEAP_A], models[CHEAP_B], models[STRONG_C]]
    policy = Policy(max_spend=MAX_SPEND, timeout_s=TIMEOUT_S)
    started = time.perf_counter()
    outcome = arbitrate_sync(
        case["text"],
        claim_output_schema(),
        providers,
        policy=policy,
        reliability=reliability,
        calibrator=calibrator,
        verifier=models[VERIFIER],
    )
    final: dict[str, Any] = {}
    decisions: dict[str, str] = {}
    n_reviewed = 0
    for name, verdict in outcome.verdicts.items():
        decisions[name] = verdict.decision
        if verdict.decision == "accept":
            final[name] = verdict.accepted_value
        elif strategy == "arbitration_review" and verdict.decision in REVIEWABLE:
            # Revisao simulada: o revisor confirma o valor do label (ou a ausencia do campo).
            final[name] = case["gold"][name]
            n_reviewed += 1
        else:
            final[name] = None
    latency = (time.perf_counter() - started) * 1000
    return CaseResult(
        strategy=strategy,
        case_id=case["id"],
        difficulty=case["difficulty"],
        final=final,
        gold=case["gold"],
        model_cost=outcome.spent_usd,
        review_cost=n_reviewed * review_cost_usd,
        n_reviewed=n_reviewed,
        latency_ms=latency,
        decisions=decisions,
        candidate_values={
            r.model: normalized_output(r.output) for r in outcome.candidates if r.usable
        },
    )


def run_strategy(
    strategy: str,
    case: dict[str, Any],
    models: dict[str, CandidateProvider],
    *,
    reliability: ReliabilityTable,
    calibrator: ConfidenceModel,
    review_cost_usd: float,
) -> CaseResult:
    if strategy == "cheap_single":
        return _single(strategy, case, [models[CHEAP_A]])
    if strategy == "strong_single":
        return _single(strategy, case, [models[STRONG_C]])
    if strategy == "majority_vote":
        return _single(strategy, case, [models[CHEAP_A], models[CHEAP_B], models[STRONG_C]])
    if strategy in ("evidence_arbitration", "arbitration_review"):
        return _arbitration(strategy, case, models, reliability, calibrator, review_cost_usd)
    raise ValueError(f"estrategia desconhecida: {strategy}")
