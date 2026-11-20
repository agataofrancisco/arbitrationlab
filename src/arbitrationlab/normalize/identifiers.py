"""Identificadores, matriculas, moedas, booleanos e texto livre.

Todas as funcoes aceitam qualquer objecto e nunca lancam excepcao: um valor inesperado
devolve `unparseable` (ou `missing` quando nao ha valor).
"""

from __future__ import annotations

import re

from arbitrationlab.normalize.result import MISSING, UNPARSEABLE, NormResult
from arbitrationlab.normalize.text import fold_key

PLATE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"[A-Z]{2}\d{4}"),  # AA-00-00
    re.compile(r"\d{2}[A-Z]{2}\d{2}"),  # 00-AA-00
    re.compile(r"\d{4}[A-Z]{2}"),  # 00-00-AA
    re.compile(r"[A-Z]{2}\d{2}[A-Z]{2}"),  # AA-00-AA
)
_POLICY = re.compile(r"[A-Z]{2}-\d{4}-\d{6}")
_CURRENCY_ALIASES = {
    "€": "EUR",
    "EURO": "EUR",
    "EUROS": "EUR",
    "EUR": "EUR",
    "$": "USD",
    "US$": "USD",
    "USD": "USD",
    "£": "GBP",
    "GBP": "GBP",
}
_TRUE = {"sim", "s", "yes", "true", "1"}
_FALSE = {"nao", "n", "no", "false", "0"}


def _clean(raw: object) -> str | None | NormResult:
    """Devolve o texto aparado, ou um NormResult (missing/unparseable) se nao for texto."""
    if raw is None:
        return MISSING
    if not isinstance(raw, str):
        return UNPARSEABLE
    stripped = raw.strip()
    return stripped if stripped else MISSING


def parse_plate(raw: object) -> NormResult:
    """Matricula portuguesa sem separadores e em maiusculas, por exemplo 'AA-12-BC' -> 'AA12BC'."""
    text = _clean(raw)
    if isinstance(text, NormResult):
        return text
    canonical = re.sub(r"[\s\-.]", "", text).upper()
    if any(p.fullmatch(canonical) for p in PLATE_PATTERNS):
        return NormResult("ok", canonical)
    return UNPARSEABLE


def parse_policy_number(raw: object) -> NormResult:
    """Numero de apolice no formato HA-aaaa-nnnnnn (aceita maiusculas e espacos)."""
    text = _clean(raw)
    if isinstance(text, NormResult):
        return text
    compact = re.sub(r"\s", "", text).upper()
    digits = re.sub(r"-", "", compact)
    if re.fullmatch(r"[A-Z]{2}\d{4}\d{6}", digits):
        canonical = f"{digits[:2]}-{digits[2:6]}-{digits[6:]}"
        if _POLICY.fullmatch(canonical):
            return NormResult("ok", canonical)
    return UNPARSEABLE


def parse_currency(raw: object) -> NormResult:
    """Codigo de moeda ISO (EUR, USD, GBP), com aliases como '€' ou 'euros'."""
    text = _clean(raw)
    if isinstance(text, NormResult):
        return text
    code = _CURRENCY_ALIASES.get(text.upper())
    return NormResult("ok", code) if code else UNPARSEABLE


def parse_bool(raw: object) -> NormResult:
    """Sim/nao. Aceita booleanos JSON, e texto em portugues ou ingles."""
    if raw is None:
        return MISSING
    if isinstance(raw, bool):
        return NormResult("ok", raw)
    text = _clean(raw)
    if isinstance(text, NormResult):
        return text
    key = fold_key(text)
    if key in _TRUE:
        return NormResult("ok", True)
    if key in _FALSE:
        return NormResult("ok", False)
    return UNPARSEABLE


def parse_text(raw: object) -> NormResult:
    """Texto livre: aparado, sem normalizar mais nada."""
    text = _clean(raw)
    if isinstance(text, NormResult):
        return text
    return NormResult("ok", text)
