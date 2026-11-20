"""Politica de arbitragem: limiares, orcamento, timeout e candidatos a usar."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Policy:
    accept_threshold: float = 0.85
    verify_threshold: float = 0.5
    max_spend: float = 0.05
    timeout_s: float = 5.0
    candidates: tuple[str, ...] | None = None
    judge: bool = False

    def __post_init__(self) -> None:
        for name in ("accept_threshold", "verify_threshold"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise ValueError(f"{name} tem de ser um numero")
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} tem de estar entre 0 e 1")
        if self.verify_threshold > self.accept_threshold:
            raise ValueError("verify_threshold nao pode ser maior que accept_threshold")
        if isinstance(self.max_spend, bool) or self.max_spend < 0:
            raise ValueError("max_spend tem de ser um numero nao negativo")
        if isinstance(self.timeout_s, bool) or self.timeout_s <= 0:
            raise ValueError("timeout_s tem de ser positivo")
