"""Validador do dataset: schema dos casos, cobertura de dificuldades e splits."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from arbitrationlab.dataset.generator import DIFFICULTIES
from arbitrationlab.schema import CLAIM_FIELDS

MIN_CASES = 100
MIN_PER_DIFFICULTY = 10
_SPLITS = {"calibration", "evaluation"}
_BOOL_FIELDS = {"third_party_involved", "injuries_reported"}
_GOLD_TYPES: dict[str, tuple[type, ...]] = {
    "policy_number": (str,),
    "incident_date": (str,),
    "license_plate": (str,),
    "claimed_amount": (float, int),
    "currency": (str,),
    "third_party_involved": (bool,),
    "injuries_reported": (bool,),
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Le um JSONL. Lanca ValueError com o numero da linha se estiver mal formado."""
    cases: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            cases.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"linha {number} invalida: {exc.msg}") from exc
    return cases


def _case_problems(case: dict[str, Any]) -> list[str]:
    cid = case.get("id", "<sem id>")
    problems: list[str] = []
    if not isinstance(case.get("text"), str) or not case["text"].strip():
        problems.append(f"{cid}: texto vazio")
    if case.get("difficulty") not in DIFFICULTIES:
        problems.append(f"{cid}: dificuldade desconhecida {case.get('difficulty')!r}")
    if case.get("split") not in _SPLITS:
        problems.append(f"{cid}: split invalido {case.get('split')!r}")
    gold = case.get("gold")
    if not isinstance(gold, dict) or set(gold) != set(CLAIM_FIELDS):
        problems.append(f"{cid}: gold deve ter exactamente os campos {CLAIM_FIELDS}")
        return problems
    for field, value in gold.items():
        if value is None:
            continue
        if field in _BOOL_FIELDS:
            if not isinstance(value, bool):
                problems.append(f"{cid}: {field} deve ser booleano")
        elif isinstance(value, bool) or not isinstance(value, _GOLD_TYPES[field]):
            problems.append(f"{cid}: tipo invalido em {field}")
    return problems


def validate_cases(cases: list[dict[str, Any]]) -> list[str]:
    """Devolve os problemas encontrados (lista vazia se o dataset estiver valido)."""
    problems: list[str] = []
    if len(cases) < MIN_CASES:
        problems.append(f"sao precisos pelo menos {MIN_CASES} casos, ha {len(cases)}")
    ids = [c.get("id") for c in cases]
    if len(set(ids)) != len(ids):
        problems.append("ids duplicados")
    for case in cases:
        problems.extend(_case_problems(case))
    counts = Counter(c.get("difficulty") for c in cases)
    for difficulty in DIFFICULTIES:
        if counts[difficulty] < MIN_PER_DIFFICULTY:
            problems.append(f"dificuldade {difficulty} com poucos casos ({counts[difficulty]})")
    return problems


def stats(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Contagens por dificuldade e split, e campos sem valor esperado (gold null)."""
    by_difficulty = Counter(c.get("difficulty") for c in cases)
    by_split = Counter(c.get("split") for c in cases)
    missing = Counter(
        field for c in cases for field, value in (c.get("gold") or {}).items() if value is None
    )
    return {
        "n_cases": len(cases),
        "by_difficulty": dict(sorted(by_difficulty.items())),
        "by_split": dict(sorted(by_split.items())),
        "gold_null_fields": dict(sorted(missing.items())),
    }
