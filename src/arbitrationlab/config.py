"""Configuracao da aplicacao lida do ambiente, com validacao defensiva.

Os tokens por defeito sao apenas de demo para desenvolvimento local e nao
sao segredos; em qualquer outro ambiente devem ser definidos por variavel.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field

ENV_PREFIX = "ARBITRATIONLAB_"
DEMO_CLIENT_TOKEN = "demo-client-token"  # noqa: S105 - token de demo, nao e segredo
DEMO_REVIEWER_TOKEN = "demo-reviewer-token"  # noqa: S105 - token de demo, nao e segredo
DEMO_CLIENT_ID = "cliente-demo"
DEMO_REVIEWER_ID = "revisor-demo"
PRINCIPAL_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def _principal_id(env: Mapping[str, str], name: str, default: str) -> str:
    raw = env.get(ENV_PREFIX + name, default).strip()
    if not PRINCIPAL_ID.fullmatch(raw):
        raise ValueError(f"{ENV_PREFIX}{name} tem de ter 1 a 64 caracteres alfanumericos, . _ -")
    return raw


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
    client_id: str = DEMO_CLIENT_ID
    reviewer_id: str = DEMO_REVIEWER_ID
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
            client_id=_principal_id(source, "CLIENT_ID", DEMO_CLIENT_ID),
            reviewer_id=_principal_id(source, "REVIEWER_ID", DEMO_REVIEWER_ID),
            max_spend_default=_float(source, "MAX_SPEND_DEFAULT", 0.05),
            candidate_timeout_s=_float(source, "CANDIDATE_TIMEOUT_S", 5.0),
            human_review_cost_usd=_float(source, "HUMAN_REVIEW_COST_USD", 0.30),
        )
