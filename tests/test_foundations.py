"""Fundacoes: configuracao, autenticacao demo e /health."""

import pytest
from fastapi.testclient import TestClient

from arbitrationlab.api.app import create_app
from arbitrationlab.api.auth import resolve_role
from arbitrationlab.config import DEMO_CLIENT_TOKEN, DEMO_REVIEWER_TOKEN, Settings


def test_health_responde_sem_autenticacao() -> None:
    client = TestClient(create_app(Settings()))
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_resolve_role_distingue_papeis() -> None:
    assert (
        resolve_role(f"Bearer {DEMO_REVIEWER_TOKEN}", DEMO_CLIENT_TOKEN, DEMO_REVIEWER_TOKEN)
        == "reviewer"
    )
    assert (
        resolve_role(f"bearer {DEMO_CLIENT_TOKEN}", DEMO_CLIENT_TOKEN, DEMO_REVIEWER_TOKEN)
        == "client"
    )


@pytest.mark.parametrize("header", [None, "", "Basic abc", "Bearer ", "Bearer errado"])
def test_resolve_role_rejeita_cabecalhos_invalidos(header: str | None) -> None:
    assert resolve_role(header, DEMO_CLIENT_TOKEN, DEMO_REVIEWER_TOKEN) is None


def test_settings_from_env_usa_defaults_e_valida_numeros() -> None:
    settings = Settings.from_env({})
    assert settings.max_spend_default == 0.05
    assert settings.client_token == DEMO_CLIENT_TOKEN
    with pytest.raises(ValueError, match="ARBITRATIONLAB_MAX_SPEND_DEFAULT"):
        Settings.from_env({"ARBITRATIONLAB_MAX_SPEND_DEFAULT": "muito"})
    with pytest.raises(ValueError, match="negativo"):
        Settings.from_env({"ARBITRATIONLAB_CANDIDATE_TIMEOUT_S": "-1"})
