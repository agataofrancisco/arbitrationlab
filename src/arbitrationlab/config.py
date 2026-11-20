"""Configuracao da aplicacao lida do ambiente, com validacao defensiva.

Os tokens por defeito sao apenas de demo para desenvolvimento local e nao
sao segredos; em qualquer outro ambiente devem ser definidos por variavel.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

ENV_PREFIX = "ARBITRATIONLAB_"
DEMO_CLIENT_TOKEN = "demo-client-token"  # noqa: S105 - token de demo, nao e segredo
DEMO_REVIEWER_TOKEN = "demo-reviewer-token"  # noqa: S105 - token de demo, nao e segredo


def _float(env: Mapping[str, str], name: str, default: float) -> float:
    raw = env.get(ENV_PREFIX + name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{ENV_PREFIX}{name} deve ser um numero, recebido {raw!r}") from exc
    if value < 0:
        raise ValueError(f"{ENV_PREFIX}{name} nao pode ser negativo")
    return value


@dataclass(frozen=True)
class Settings:
    database_url: str = "sqlite:///./data/arbitrationlab.db"
    client_token: str = DEMO_CLIENT_TOKEN
    reviewer_token: str = DEMO_REVIEWER_TOKEN
    max_spend_default: float = 0.05
    candidate_timeout_s: float = 5.0
    human_review_cost_usd: float = 0.30
    extra: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        source = os.environ if env is None else env
        return cls(
            database_url=source.get(ENV_PREFIX + "DATABASE_URL", cls.database_url),
            client_token=source.get(ENV_PREFIX + "CLIENT_TOKEN", DEMO_CLIENT_TOKEN),
            reviewer_token=source.get(ENV_PREFIX + "REVIEWER_TOKEN", DEMO_REVIEWER_TOKEN),
            max_spend_default=_float(source, "MAX_SPEND_DEFAULT", 0.05),
            candidate_timeout_s=_float(source, "CANDIDATE_TIMEOUT_S", 5.0),
            human_review_cost_usd=_float(source, "HUMAN_REVIEW_COST_USD", 0.30),
        )
