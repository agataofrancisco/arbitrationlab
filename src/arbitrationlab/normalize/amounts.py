"""Montantes: numeros em formato pt-PT ou en, e montantes escritos por extenso em portugues.

Formato pt-PT: "1.250,50 €" -> 1250.5. Formato en: "1,250.50" -> 1250.5. Sem digitos,
tenta-se a leitura por extenso: "mil duzentos e cinquenta euros e cinquenta cêntimos".
"""

from __future__ import annotations

import math
import re

from arbitrationlab.normalize.numerals import words_to_int
from arbitrationlab.normalize.result import MISSING, UNPARSEABLE, NormResult
from arbitrationlab.normalize.text import fold_key

_CURRENCY_SYMBOLS = re.compile(r"(?i)(US\$|€|£|\$|\b(?:EUR|USD|GBP)\b)")
_EURO_TOKEN = re.compile(r"(?i)\beuros?\b")
_PT = re.compile(r"\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+(?:,\d{1,2})?")
_EN = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?")
_EURO_WORDS = {"euro", "euros"}
_CENT_WORDS = {"centimo", "centimos", "cent", "cents"}


def _from_digits(text: str) -> float | None:
    compact = re.sub(r"\s+", "", text)
    if _PT.fullmatch(compact):
        return float(compact.replace(".", "").replace(",", "."))
    if _EN.fullmatch(compact):
        return float(compact.replace(",", ""))
    return None


def _from_words(text: str) -> float | None:
    tokens = fold_key(text).replace(",", " ").split()
    if not tokens:
        return None
    euros_at = next((i for i, t in enumerate(tokens) if t in _EURO_WORDS), None)
    cents_at = next((i for i, t in enumerate(tokens) if t in _CENT_WORDS), None)
    if cents_at is not None:
        if euros_at is None or cents_at != len(tokens) - 1:
            return None
        int_tokens = tokens[:euros_at]
        cent_tokens = [t for t in tokens[euros_at + 1 : cents_at] if t != "e"]
    else:
        if euros_at is not None and euros_at != len(tokens) - 1:
            return None
        int_tokens = tokens[:euros_at] if euros_at is not None else tokens
        cent_tokens = []
    try:
        whole = words_to_int(int_tokens)
        cents = words_to_int(cent_tokens) if cent_tokens else 0
    except ValueError:
        return None
    return whole + cents / 100


def parse_amount(raw: object) -> NormResult:
    """Normaliza para float com 2 casas. Montantes negativos ou nao finitos sao rejeitados."""
    if raw is None:
        return MISSING
    if isinstance(raw, bool):
        return UNPARSEABLE
    if isinstance(raw, int | float):
        if math.isfinite(raw) and raw >= 0:
            return NormResult("ok", round(float(raw), 2))
        return UNPARSEABLE
    if not isinstance(raw, str):
        return UNPARSEABLE
    core = _CURRENCY_SYMBOLS.sub(" ", raw).strip()
    if not core:
        return MISSING
    if re.search(r"\d", core):
        value = _from_digits(_EURO_TOKEN.sub(" ", core).strip())
    else:
        value = _from_words(core)
    if value is None or not math.isfinite(value) or value < 0:
        return UNPARSEABLE
    return NormResult("ok", round(value, 2))
