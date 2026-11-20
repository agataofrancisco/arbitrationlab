"""Geracao paralela de candidatos com timeout por chamada e orcamento por arbitragem.

O orcamento e reservado de forma sequencial, antes de qualquer chamada ser iniciada.
Assim o resultado nao depende da ordem de conclusao dos fornecedores.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from arbitrationlab.generation.providers import CandidateProvider
from arbitrationlab.schema import validate_candidate_output

SKIPPED_BUDGET = "skipped: budget"


@dataclass(frozen=True)
class CandidateRecord:
    model: str
    status: str  # ok | timed_out | invalid | error | skipped
    output: dict[str, Any] | None
    cost_usd: float
    latency_ms: float
    reason: str | None = None
    errors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def usable(self) -> bool:
        return self.status == "ok" and self.output is not None


class BudgetLedger:
    """Contabilidade do `max_spend` de uma arbitragem."""

    def __init__(self, max_spend: float) -> None:
        if isinstance(max_spend, bool) or not isinstance(max_spend, int | float):
            raise ValueError("max_spend tem de ser um numero")
        if max_spend < 0:
            raise ValueError("max_spend nao pode ser negativo")
        self.max_spend = float(max_spend)
        self.spent = 0.0

    def try_reserve(self, cost: float) -> bool:
        if self.spent + cost > self.max_spend + 1e-12:
            return False
        self.spent += cost
        return True


async def _call_one(
    provider: CandidateProvider,
    text: str,
    schema: dict[str, Any],
    timeout_s: float,
) -> CandidateRecord:
    started = time.perf_counter()
    cost = provider.cost_per_call_usd

    def elapsed_ms() -> float:
        return (time.perf_counter() - started) * 1000

    try:
        output = await asyncio.wait_for(provider.extract(text, schema), timeout=timeout_s)
    except TimeoutError:
        return CandidateRecord(provider.name, "timed_out", None, cost, elapsed_ms())
    except Exception as exc:  # noqa: BLE001 - qualquer falha do fornecedor vira estado do candidato
        return CandidateRecord(
            provider.name, "error", None, cost, elapsed_ms(), reason=type(exc).__name__
        )
    errors = validate_candidate_output(schema, output)
    if errors:
        return CandidateRecord(
            provider.name, "invalid", None, cost, elapsed_ms(), errors=tuple(errors)
        )
    return CandidateRecord(provider.name, "ok", output, cost, elapsed_ms())


async def generate_candidates(
    text: str,
    schema: dict[str, Any],
    providers: Sequence[CandidateProvider],
    *,
    timeout_s: float,
    max_spend: float | None = None,
    ledger: BudgetLedger | None = None,
) -> list[CandidateRecord]:
    """Corre os fornecedores em paralelo e devolve um registo por fornecedor, pela mesma ordem.

    Passa-se `max_spend` (orcamento novo) ou um `ledger` partilhado com as verificacoes.
    """
    if not isinstance(text, str):
        raise ValueError("o texto tem de ser uma string")
    if isinstance(timeout_s, bool) or not isinstance(timeout_s, int | float) or timeout_s <= 0:
        raise ValueError("timeout_s tem de ser um numero positivo")
    if ledger is None:
        if max_spend is None:
            raise ValueError("indique max_spend ou um ledger")
        ledger = BudgetLedger(max_spend)
    records: list[CandidateRecord | None] = [None] * len(providers)
    pending: list[tuple[int, asyncio.Task[CandidateRecord]]] = []
    for index, provider in enumerate(providers):
        if not ledger.try_reserve(provider.cost_per_call_usd):
            records[index] = CandidateRecord(
                provider.name, "skipped", None, 0.0, 0.0, reason=SKIPPED_BUDGET
            )
            continue
        task = asyncio.ensure_future(_call_one(provider, text, schema, timeout_s))
        pending.append((index, task))
    for index, task in pending:
        records[index] = await task
    return [record for record in records if record is not None]
