"""Casos desfavoraveis: erros correlacionados, erros aceites, custo sem ganho e sensibilidade."""

from __future__ import annotations

from typing import Any

from arbitrationlab.experiments.metrics import exact_match_by_case
from arbitrationlab.experiments.strategies import CaseResult, same_value
from arbitrationlab.generation.registry import CHEAP_A, CHEAP_B
from arbitrationlab.schema import CLAIM_FIELDS, claim_output_schema, field_specs

_TYPES = {name: spec["x-type"] for name, spec in field_specs(claim_output_schema()).items()}
SENSITIVITY_COSTS: tuple[float, ...] = (0.05, 0.30, 1.00)


def correlated_date_errors(
    cases: dict[str, dict[str, Any]],
    evidence: list[CaseResult],
    majority: list[CaseResult],
) -> dict[str, Any]:
    """Casos em que cheap-a e cheap-b dao a mesma data errada. Conta quantos a evidencia apanhou."""
    evidence_by_id = {r.case_id: r for r in evidence}
    majority_by_id = {r.case_id: r for r in majority}
    examples: list[dict[str, Any]] = []
    caught = escaped = 0
    for case_id, case in cases.items():
        result = evidence_by_id.get(case_id)
        if result is None or not result.candidate_values:
            continue
        a = result.candidate_values.get(CHEAP_A, {}).get("incident_date")
        b = result.candidate_values.get(CHEAP_B, {}).get("incident_date")
        gold = case["gold"]["incident_date"]
        if a is None or b is None or a != b or a == gold:
            continue
        decision = result.decisions.get("incident_date")
        was_caught = decision != "accept"
        caught += was_caught
        escaped += not was_caught
        examples.append(
            {
                "case_id": case_id,
                "gold": gold,
                "wrong_value": a,
                "evidence_decision": decision,
                "evidence_reason_caught": was_caught,
                "majority_final": majority_by_id[case_id].final["incident_date"]
                if case_id in majority_by_id
                else None,
            }
        )
    return {"total": caught + escaped, "caught": caught, "escaped": escaped, "examples": examples}


def accepted_wrong(evidence: list[CaseResult]) -> list[dict[str, Any]]:
    """Valores aceites automaticamente que estao errados (erros que a evidencia nao apanhou)."""
    found: list[dict[str, Any]] = []
    for r in evidence:
        for name in CLAIM_FIELDS:
            if r.decisions.get(name) != "accept":
                continue
            if not same_value(_TYPES[name], r.final.get(name), r.gold.get(name)):
                found.append(
                    {
                        "case_id": r.case_id,
                        "difficulty": r.difficulty,
                        "field": name,
                        "accepted": r.final.get(name),
                        "gold": r.gold.get(name),
                    }
                )
    return found


def cost_without_gain(cheap: list[CaseResult], review: list[CaseResult]) -> dict[str, Any]:
    """Casos em que a arbitragem com revisao custa mais do que o modelo barato, que ja acertava."""
    cheap_by_id = {r.case_id: r for r in cheap}
    exact_cheap = exact_match_by_case(cheap)
    ids: list[str] = []
    for r in review:
        base = cheap_by_id[r.case_id]
        if exact_cheap[r.case_id] and r.model_cost + r.review_cost > base.model_cost:
            ids.append(r.case_id)
    return {"count": len(ids), "case_ids": ids[:10]}


def review_cost_sensitivity(review: list[CaseResult]) -> list[dict[str, float]]:
    """Custo medio por caso da arbitragem com revisao para varios custos de revisao por campo."""
    n = len(review) or 1
    model = sum(r.model_cost for r in review) / n
    reviewed = sum(r.n_reviewed for r in review) / n
    return [
        {"review_cost_usd": c, "mean_cost_usd": model + reviewed * c} for c in SENSITIVITY_COSTS
    ]
