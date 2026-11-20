"""Fornecedores de candidatos: protocolo, mocks deterministas e perfis de erro.

Os mocks nao vem o gold. Leem os rotulos "Campo: valor" do documento (como um modelo fraco
faria) e aplicam um perfil de erro. O erro e decidido por um hash do documento, por isso
e reprodutivel. Com `correlated=True`, dois modelos com o mesmo perfil erram da mesma forma.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from arbitrationlab.normalize.text import fold_key
from arbitrationlab.schema import field_specs

ErrorKind = Literal[
    "clean", "date_swap", "invent_amount", "omit_field", "bad_schema", "timeout", "error"
]
Parser = Literal["cheap", "strong"]

_DATE_DMY = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
_BOOL_WORDS = {"sim": True, "nao": False, "não": False}


class ProviderError(Exception):
    """Falha de um fornecedor (rede, quota, resposta mal formada)."""


class CandidateProvider(Protocol):
    name: str
    cost_per_call_usd: float

    async def extract(self, text: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Devolve um objecto JSON com os campos do schema. Pode lancar ProviderError."""
        ...


@dataclass(frozen=True)
class ErrorProfile:
    """Perfil de erro de um mock. `rate` e a fracao de documentos afectados."""

    kind: ErrorKind = "clean"
    rate: float = 0.0
    correlated: bool = False
    latency_s: float = 0.0
    field: str = "license_plate"


def _unit_hash(*parts: str) -> float:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return int(digest[:12], 16) / 0xFFFFFFFFFFFF


def _labeled_value(text: str, label: str, strong: bool) -> str | None:
    """Primeira linha 'rotulo: valor' cujo rotulo comeca por `label` (sem acentos)."""
    wanted = fold_key(label)
    for line in text.splitlines():
        head, sep, value = line.partition(":")
        if not sep:
            continue
        head_key = fold_key(head)
        if strong and "(" in head_key:
            continue
        if head_key.startswith(wanted):
            return value.strip()
    return None


def parse_labeled_fields(text: str, schema: dict[str, Any], *, strong: bool) -> dict[str, Any]:
    """Extrai os campos pelos rotulos. Em modo `strong` ignora rotulos com parenteses."""
    output: dict[str, Any] = {}
    for field, spec in field_specs(schema).items():
        raw = _labeled_value(text, spec["x-label"], strong) if spec["x-label"] else None
        if raw is None or raw == "":
            output[field] = None
        elif spec["x-type"] == "bool":
            output[field] = _BOOL_WORDS.get(fold_key(raw), raw)
        else:
            output[field] = raw
    return output


class MockProvider:
    """Fornecedor deterministico sem rede, para CI e experiencias em mock."""

    def __init__(
        self,
        name: str,
        *,
        parser: Parser,
        cost_per_call_usd: float,
        profile: ErrorProfile | None = None,
    ) -> None:
        self.name = name
        self.parser = parser
        self.cost_per_call_usd = cost_per_call_usd
        self.profile = profile or ErrorProfile()

    def _hits(self, text: str) -> bool:
        if self.profile.rate <= 0:
            return False
        key = text if self.profile.correlated else f"{self.name}|{text}"
        return _unit_hash("hit", key) < self.profile.rate

    async def extract(self, text: str, schema: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(text, str):
            raise ProviderError("o texto tem de ser uma string")
        if self.profile.kind == "timeout":
            await asyncio.sleep(self.profile.latency_s)
        if self.profile.kind == "error":
            raise ProviderError(f"erro simulado em {self.name}")
        output = parse_labeled_fields(text, schema, strong=self.parser == "strong")
        if not self._hits(text):
            return output
        return self._apply_error(output)

    def _apply_error(self, output: dict[str, Any]) -> dict[str, Any]:
        kind = self.profile.kind
        if kind == "date_swap":
            output["incident_date"] = _swap_day_month(output.get("incident_date"))
        elif kind == "invent_amount" and output.get("claimed_amount") is not None:
            output["claimed_amount"] = "7.777,77 €"
        elif kind == "omit_field":
            output[self.profile.field] = None
        elif kind == "bad_schema":
            output["policy_number"] = 12345
        return output


def _swap_day_month(raw: Any) -> Any:
    """Le uma data dd/mm/aaaa e devolve a leitura trocada em ISO (erro tipico de locale)."""
    if not isinstance(raw, str):
        return raw
    match = _DATE_DMY.match(raw.strip())
    if not match:
        return raw
    first, second, year = int(match.group(1)), int(match.group(2)), match.group(3)
    if not (1 <= first <= 12 and 1 <= second <= 12) or first == second:
        return raw
    return f"{year}-{first:02d}-{second:02d}"
