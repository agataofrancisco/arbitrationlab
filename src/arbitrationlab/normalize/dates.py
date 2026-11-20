"""Datas: ISO 8601, formato "d de mes de aaaa" e dd/mm/aaaa (com ambiguidade explicita).

Regra: um numero "a/b/aaaa" e ambiguo quando a e b sao ambos <= 12 e as duas leituras
(dia/mes e mes/dia) sao datas validas e diferentes. Nesse caso o campo fica `ambiguous`,
nunca se escolhe uma leitura por convencao.
"""

from __future__ import annotations

import re
from datetime import date

from arbitrationlab.normalize.result import MISSING, UNPARSEABLE, NormResult
from arbitrationlab.normalize.text import fold_key

MONTHS_PT: dict[str, int] = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}
_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_WORDS = re.compile(r"^(\d{1,2}) de ([a-z]+) de (\d{4})$")
_NUMERIC = re.compile(r"^(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})$")
_MIN_YEAR, _MAX_YEAR = 1900, 2100


def _build(year: int, month: int, day: int) -> str | None:
    if not _MIN_YEAR <= year <= _MAX_YEAR:
        return None
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def parse_date(raw: object) -> NormResult:
    """Normaliza para ISO 8601. Nunca lanca excepcao."""
    if raw is None:
        return MISSING
    if not isinstance(raw, str):
        return UNPARSEABLE
    text = raw.strip()
    if not text:
        return MISSING
    iso = _ISO.match(text)
    if iso:
        value = _build(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
        return NormResult("ok", value) if value else UNPARSEABLE
    words = _WORDS.match(fold_key(text))
    if words:
        month = MONTHS_PT.get(words.group(2))
        if month is None:
            return UNPARSEABLE
        value = _build(int(words.group(3)), month, int(words.group(1)))
        return NormResult("ok", value) if value else UNPARSEABLE
    numeric = _NUMERIC.match(text)
    if numeric:
        first, second = int(numeric.group(1)), int(numeric.group(2))
        year = int(numeric.group(3))
        dmy = _build(year, second, first)
        mdy = _build(year, first, second)
        options = tuple(dict.fromkeys(o for o in (dmy, mdy) if o is not None))
        if not options:
            return UNPARSEABLE
        if len(options) == 1:
            return NormResult("ok", options[0])
        return NormResult("ambiguous", options=options)
    return UNPARSEABLE
