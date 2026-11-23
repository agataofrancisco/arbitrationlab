"""Adaptador opcional: a arbitragem como avaliador do RegressionGuard.

Requer o extra `regressionguard` (`pip install -e ".[regressionguard]"`). Sem ele, importar este
modulo falha com ImportError; o resto do ArbitrationLab nao depende dele.

O que expõe:
- `arbitrationlab.claim_fields`: avaliador registado no registo do RegressionGuard. Passa se a
  arbitragem nunca aceitou um valor errado. Campos em revisao ou abstencao nao contam como erro.
- `arbitration_output`: corre a arbitragem (mock) sobre um texto e devolve um `TargetOutput`.
- `run_claim_suite`: corre um dataset golden do RegressionGuard sobre a arbitragem, usando a
  API publica (`load_dataset`, `evaluate_output`). Nao usa `run_suite`, porque essa funcao so
  constroi alvos da fabrica interna do RegressionGuard.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from regressionguard import EvalContext, EvalResult, evaluator_names, load_dataset, register
from regressionguard.runner.run import evaluate_output
from regressionguard.targets.base import TargetOutput

from arbitrationlab.decision import Policy
from arbitrationlab.generation.registry import (
    CHEAP_A,
    CHEAP_B,
    STRONG_C,
    VERIFIER,
    default_mock_models,
)
from arbitrationlab.pipeline import arbitrate_sync
from arbitrationlab.schema import CLAIM_FIELDS, claim_output_schema

EVALUATOR_NAME = "arbitrationlab.claim_fields"
TARGET_NAME = "arbitrationlab-claims"
CANDIDATES: tuple[str, ...] = (CHEAP_A, CHEAP_B, STRONG_C)
AMOUNT_TOLERANCE = 0.005


def _equal(accepted: Any, gold: Any) -> bool:
    if accepted is None or gold is None:
        return accepted is None and gold is None
    if isinstance(accepted, int | float) and isinstance(gold, int | float):
        if isinstance(accepted, bool) or isinstance(gold, bool):
            return accepted == gold
        return abs(float(accepted) - float(gold)) < AMOUNT_TOLERANCE
    return accepted == gold


def claim_fields(ctx: EvalContext) -> EvalResult:
    """Passa se nenhum campo decidido automaticamente ('accept') difere do gold."""
    data = ctx.output.data
    expected = ctx.case.expected
    if not isinstance(data, dict) or not isinstance(expected, dict):
        return EvalResult(passed=False, reason="no_arbitration_output")
    accepted = data.get("accepted") or {}
    decisions = data.get("decisions") or {}
    decided = 0
    wrong: list[str] = []
    for name in CLAIM_FIELDS:
        if decisions.get(name) != "accept":
            continue
        decided += 1
        if not _equal(accepted.get(name), expected.get(name)):
            wrong.append(name)
    details: dict[str, Any] = {
        "decided": decided,
        "undecided": len(CLAIM_FIELDS) - decided,
        "accepted_wrong": wrong,
    }
    if wrong:
        score = (decided - len(wrong)) / decided if decided else 0.0
        return EvalResult(
            passed=False, score=score, reason=f"accepted_wrong:{wrong[0]}", details=details
        )
    return EvalResult(passed=True, score=1.0, details=details)


def ensure_registered() -> None:
    """Regista o avaliador uma unica vez (o registo do RegressionGuard recusa duplicados)."""
    if EVALUATOR_NAME not in evaluator_names():
        register(
            EVALUATOR_NAME,
            description="A arbitragem nunca aceita um valor de campo diferente do gold.",
        )(claim_fields)


ensure_registered()


def arbitration_output(text: str) -> TargetOutput:
    """Corre a arbitragem (mock) sobre o texto e devolve a saida normalizada."""
    models = default_mock_models()
    started = time.perf_counter()
    outcome = arbitrate_sync(
        text,
        claim_output_schema(),
        [models[name] for name in CANDIDATES],
        policy=Policy(max_spend=0.05, timeout_s=5.0),
        verifier=models[VERIFIER],
    )
    accepted = {name: v.accepted_value for name, v in outcome.verdicts.items()}
    decisions = {name: v.decision for name, v in outcome.verdicts.items()}
    return TargetOutput(
        text=f"aceites: {sum(d == 'accept' for d in decisions.values())}/{len(decisions)}",
        data={
            "accepted": accepted,
            "decisions": decisions,
            "suspected_injection": outcome.suspected_injection,
        },
        cost_usd=outcome.spent_usd,
        latency_ms=(time.perf_counter() - started) * 1000,
    )


@dataclass(frozen=True)
class CaseOutcome:
    case_id: str
    category: str
    severity: str
    passed: bool
    reason: str | None


def run_claim_suite(dataset_path: Path, *, root: Path) -> list[CaseOutcome]:
    """Corre cada caso do dataset golden pela arbitragem e pelos avaliadores do RegressionGuard."""
    dataset = load_dataset(dataset_path)
    results: list[CaseOutcome] = []
    for case in dataset.cases:
        output = arbitration_output(case.input)
        records, primary_ok = evaluate_output(case, output, root, None)
        failed = [r for r in records if not r.passed and not r.secondary]
        passed = primary_ok and not failed
        reason = failed[0].reason if failed else None
        results.append(CaseOutcome(case.id, case.category, case.severity, passed, reason))
    return results


def build_smoke_dataset(claims_path: Path, out_path: Path) -> Path:
    """Gera o dataset de smoke (1 caso por dificuldade) no formato golden do RegressionGuard.

    Os casos vem do dataset sintetico versionado; os `expected` sao os seus labels (gold).
    """
    cases = [json.loads(line) for line in claims_path.read_text(encoding="utf-8").splitlines()]
    seen: set[str] = set()
    selected: list[dict[str, Any]] = []
    for case in cases:
        if case["difficulty"] in seen:
            continue
        seen.add(case["difficulty"])
        selected.append(case)
    manifest = {
        "manifest": {
            "name": "arbitrationlab-claims-smoke",
            "version": "0.1.0",
            "target": TARGET_NAME,
            "description": "Um caso por dificuldade do dataset sintetico de sinistros (mock).",
            "author": "arbitrationlab",
            "date": date(2026, 11, 21).isoformat(),
        }
    }
    lines = [json.dumps(manifest, ensure_ascii=False)]
    for case in selected:
        record = {
            "id": case["id"],
            "input": case["text"],
            "expected": case["gold"],
            "category": case["difficulty"],
            "severity": "critical"
            if case["difficulty"] in ("injection", "inconsistent_amount")
            else "normal",
            "source": f"dataset-sintetico:{case['id']}",
            "evaluators": [EVALUATOR_NAME],
        }
        lines.append(json.dumps(record, ensure_ascii=False, sort_keys=True))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return out_path
