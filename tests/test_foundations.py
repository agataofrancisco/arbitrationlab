"""Fundacoes: configuracao, autenticacao demo e /health."""

import pytest
from fastapi.testclient import TestClient

from arbitrationlab.api.app import create_app
from arbitrationlab.api.auth import Principal, resolve_principal
from arbitrationlab.config import (
    DEMO_CLIENT_ID,
    DEMO_CLIENT_TOKEN,
    DEMO_REVIEWER_ID,
    DEMO_REVIEWER_TOKEN,
    Settings,
)


def _resolve(header: str | None) -> Principal | None:
    return resolve_principal(
        header,
        client_token=DEMO_CLIENT_TOKEN,
        client_id=DEMO_CLIENT_ID,
        reviewer_token=DEMO_REVIEWER_TOKEN,
        reviewer_id=DEMO_REVIEWER_ID,
    )


def test_health_responde_sem_autenticacao() -> None:
    client = TestClient(create_app(Settings()))
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_settings_from_env_usa_defaults_e_valida_numeros() -> None:
    settings = Settings.from_env({})
    assert settings.max_spend_default == 0.05
    assert settings.client_token == DEMO_CLIENT_TOKEN
    with pytest.raises(ValueError, match="ARBITRATIONLAB_MAX_SPEND_DEFAULT"):
        Settings.from_env({"ARBITRATIONLAB_MAX_SPEND_DEFAULT": "muito"})
    with pytest.raises(ValueError, match="negativo"):
        Settings.from_env({"ARBITRATIONLAB_CANDIDATE_TIMEOUT_S": "-1"})


@pytest.mark.parametrize("header", [None, "", "Basic abc", "Bearer ", "Bearer errado"])
def test_resolve_principal_rejeita_cabecalhos_invalidos(header: str | None) -> None:
    assert _resolve(header) is None


def test_resolve_principal_mapeia_cada_token_para_principal_fixo() -> None:
    assert _resolve(f"Bearer {DEMO_REVIEWER_TOKEN}") == Principal(DEMO_REVIEWER_ID, "reviewer")
    assert _resolve(f"bearer {DEMO_CLIENT_TOKEN}") == Principal(DEMO_CLIENT_ID, "client")
