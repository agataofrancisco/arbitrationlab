"""Normalizacao por tipo de campo. Cada tipo do schema (`x-type`) tem um parser proprio."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from arbitrationlab.normalize.amounts import parse_amount
from arbitrationlab.normalize.dates import parse_date
from arbitrationlab.normalize.identifiers import (
    parse_bool,
    parse_currency,
    parse_plate,
    parse_policy_number,
    parse_text,
)
from arbitrationlab.normalize.result import NormResult

PARSERS: dict[str, Callable[[object], NormResult]] = {
    "date": parse_date,
    "amount": parse_amount,
    "plate": parse_plate,
    "id": parse_policy_number,
    "currency": parse_currency,
    "bool": parse_bool,
    "text": parse_text,
}


def normalize(field_type: str, raw: Any) -> NormResult:
    """Normaliza `raw` segundo o tipo. Tipos desconhecidos tratam-se como texto."""
    parser = PARSERS.get(field_type, parse_text)
    return parser(raw)


__all__ = ["PARSERS", "NormResult", "normalize"]
