"""Fiabilidade historica por (modelo, campo), com prior Beta.

A media posterior de Beta(alpha0 + acertos, beta0 + erros) estima a probabilidade de um
modelo acertar num campo. Um par (modelo, campo) sem historico parte do prior (0.5 com
alpha0 = beta0 = 1). So se alimenta com casos rotulados do split de calibracao.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field


@dataclass
class ReliabilityTable:
    alpha0: float = 1.0
    beta0: float = 1.0
    _counts: dict[tuple[str, str], list[int]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.alpha0 <= 0 or self.beta0 <= 0:
            raise ValueError("os parametros do prior Beta tem de ser positivos")

    def observe(self, model: str, field_name: str, correct: bool) -> None:
        counts = self._counts.setdefault((model, field_name), [0, 0])
        counts[0 if correct else 1] += 1

    def observe_many(self, observations: Iterable[tuple[str, str, bool]]) -> None:
        for model, field_name, correct in observations:
            self.observe(model, field_name, correct)

    def counts(self, model: str, field_name: str) -> tuple[int, int]:
        hits, misses = self._counts.get((model, field_name), [0, 0])
        return hits, misses

    def mean(self, model: str, field_name: str) -> float:
        hits, misses = self.counts(model, field_name)
        alpha = self.alpha0 + hits
        beta = self.beta0 + misses
        return alpha / (alpha + beta)
