"""Resultado da normalizacao de um valor bruto."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

NormStatus = Literal["ok", "missing", "unparseable", "ambiguous"]


@dataclass(frozen=True)
class NormResult:
    """`ok` traz `value`. `ambiguous` traz as leituras possiveis em `options`."""

    status: NormStatus
    value: Any = None
    options: tuple[Any, ...] = ()

    @property
    def ok(self) -> bool:
        return self.status == "ok"


MISSING = NormResult("missing")
UNPARSEABLE = NormResult("unparseable")
