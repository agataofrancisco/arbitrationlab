"""Localizacao de evidencia: um valor so tem evidencia se uma leitura do texto lhe corresponde.

- exacta: a leitura normaliza para o mesmo valor (score 1.0).
- aproximada: so para matriculas, com semelhanca >= 0.8 (score 0.5).
- nenhuma: score 0.0. Um valor sem evidencia nunca e aceite automaticamente.
Leituras marcadas `tainted` (linhas com instrucoes) nao contam.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from arbitrationlab.evidence.readings import Reading

FUZZY_THRESHOLD = 0.8
EXACT_SCORE = 1.0
FUZZY_SCORE = 0.5
AMOUNT_TOLERANCE = 0.005


@dataclass(frozen=True)
class Evidence:
    score: float
    method: str  # exact | fuzzy | none
    start: int | None = None
    end: int | None = None
    text: str | None = None


NO_EVIDENCE = Evidence(score=0.0, method="none")


def _same(field_type: str, left: Any, right: Any) -> bool:
    if field_type == "amount":
        return abs(float(left) - float(right)) < AMOUNT_TOLERANCE
    return left == right


def _span(reading: Reading, method: str, score: float) -> Evidence:
    return Evidence(
        score=score, method=method, start=reading.start, end=reading.end, text=reading.raw
    )


def locate(field_type: str, value: Any, readings: list[Reading]) -> Evidence:
    """Procura a evidencia de `value` entre as leituras do campo."""
    if value is None:
        return NO_EVIDENCE
    usable = [r for r in readings if not r.tainted]
    for reading in usable:
        if reading.result.ok and _same(field_type, reading.result.value, value):
            return _span(reading, "exact", EXACT_SCORE)
    if field_type == "plate" and isinstance(value, str):
        best: tuple[float, Reading] | None = None
        for reading in usable:
            compact = "".join(ch for ch in reading.raw.upper() if ch.isalnum())
            ratio = SequenceMatcher(None, compact, value).ratio()
            if ratio >= FUZZY_THRESHOLD and (best is None or ratio > best[0]):
                best = (ratio, reading)
        if best is not None:
            return _span(best[1], "fuzzy", FUZZY_SCORE)
    return NO_EVIDENCE


def ambiguous_options(readings: list[Reading]) -> set[str]:
    """Todas as datas ou valores possiveis de leituras ambiguas e nao marcadas."""
    options: set[str] = set()
    for reading in readings:
        if not reading.tainted and reading.result.status == "ambiguous":
            options.update(str(o) for o in reading.result.options)
    return options


def other_values(field_type: str, value: Any, readings: list[Reading]) -> list[Any]:
    """Valores normalizados (nao marcados) diferentes de `value`."""
    values: list[Any] = []
    for reading in readings:
        if reading.tainted or not reading.result.ok:
            continue
        candidate = reading.result.value
        if not _same(field_type, candidate, value):
            values.append(candidate)
    return values
