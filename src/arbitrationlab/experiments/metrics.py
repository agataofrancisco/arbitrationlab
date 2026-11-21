"""Metricas por estrategia: exact match, F1 por campo, cobertura, erros criticos e custo."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Any

from arbitrationlab.experiments.strategies import CaseResult, same_value
from arbitrationlab.schema import CLAIM_FIELDS, claim_output_schema, field_specs

_TYPES = {name: spec["x-type"] for name, spec in field_specs(claim_output_schema()).items()}


def _safe_div(num: float, den: float) -> float:
    return num / den if den else 0.0


def field_scores(results: list[CaseResult]) -> dict[str, dict[str, float]]:
    """TP/FP/FN por campo. Um valor so conta como acerto se for igual ao gold (nao nulo)."""
    scores: dict[str, dict[str, float]] = {}
    for name in CLAIM_FIELDS:
        tp = fp = fn = 0
        for r in results:
            pred, gold = r.final.get(name), r.gold.get(name)
            correct = gold is not None and same_value(_TYPES[name], pred, gold)
            if correct:
                tp += 1
            else:
                if pred is not None:
                    fp += 1
                if gold is not None:
                    fn += 1
        precision = _safe_div(tp, tp + fp)
        recall = _safe_div(tp, tp + fn)
        f1 = _safe_div(2 * precision * recall, precision + recall)
        scores[name] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
    return scores


def exact_match(results: list[CaseResult]) -> float:
    """Fracao de casos com todos os campos iguais ao gold (ausentes contam como certos)."""
    hits = 0
    for r in results:
        if all(same_value(_TYPES[n], r.final.get(n), r.gold.get(n)) for n in CLAIM_FIELDS):
            hits += 1
    return _safe_div(hits, len(results))


def critical_error_rate(results: list[CaseResult]) -> float:
    """Campos com valor decidido e errado (aceites erradamente), sobre todos os campos."""
    total = len(results) * len(CLAIM_FIELDS)
    errors = 0
    for r in results:
        for n in CLAIM_FIELDS:
            pred = r.final.get(n)
            if pred is not None and not same_value(_TYPES[n], pred, r.gold.get(n)):
                errors += 1
    return _safe_div(errors, total)


def coverage(results: list[CaseResult]) -> float:
    """Fracao de campos com um valor final (decidido automaticamente ou revisto)."""
    total = len(results) * len(CLAIM_FIELDS)
    decided = sum(1 for r in results for n in CLAIM_FIELDS if r.final.get(n) is not None)
    return _safe_div(decided, total)


def summarize(results: list[CaseResult]) -> dict[str, Any]:
    scores = field_scores(results)
    n = len(results)
    by_difficulty: dict[str, list[CaseResult]] = defaultdict(list)
    for r in results:
        by_difficulty[r.difficulty].append(r)
    model_cost = [r.model_cost for r in results]
    review_cost = [r.review_cost for r in results]
    return {
        "cases": n,
        "exact_match": exact_match(results),
        "macro_f1": mean(s["f1"] for s in scores.values()),
        "field_f1": {k: v["f1"] for k, v in scores.items()},
        "coverage": coverage(results),
        "critical_error_rate": critical_error_rate(results),
        "review_rate": _safe_div(sum(r.n_reviewed for r in results), n * len(CLAIM_FIELDS)),
        "mean_model_cost_usd": mean(model_cost) if n else 0.0,
        "mean_review_cost_usd": mean(review_cost) if n else 0.0,
        "mean_cost_usd": mean(c + v for c, v in zip(model_cost, review_cost, strict=True))
        if n
        else 0.0,
        "total_cost_usd": sum(model_cost) + sum(review_cost),
        "mean_latency_ms": mean(r.latency_ms for r in results) if n else 0.0,
        "exact_match_by_difficulty": {
            d: exact_match(rs) for d, rs in sorted(by_difficulty.items())
        },
    }


def exact_match_by_case(results: list[CaseResult]) -> dict[str, bool]:
    return {
        r.case_id: all(same_value(_TYPES[n], r.final.get(n), r.gold.get(n)) for n in CLAIM_FIELDS)
        for r in results
    }
