"""API HTTP: papeis (401/403), validacao (422), revisao humana com auditoria, falhas e metricas."""

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from arbitrationlab.api.app import create_app
from arbitrationlab.config import DEMO_CLIENT_TOKEN, DEMO_REVIEWER_TOKEN, Settings
from arbitrationlab.dataset.validate import load_jsonl
from arbitrationlab.schema import claim_output_schema

ROOT = Path(__file__).resolve().parents[1]
CASES = load_jsonl(ROOT / "datasets" / "claims" / "claims.jsonl")
CLIENT = {"Authorization": f"Bearer {DEMO_CLIENT_TOKEN}"}
REVIEWER = {"Authorization": f"Bearer {DEMO_REVIEWER_TOKEN}", "X-Actor": "revisora.ana"}


@pytest.fixture
def client() -> TestClient:
    settings = Settings(database_url="sqlite://")
    return TestClient(create_app(settings))


def _create(client: TestClient, text: str, **extra: Any) -> str:
    body: dict[str, Any] = {
        "task_id": "sinistro-teste",
        "text": text,
        "output_schema": claim_output_schema(),
        "policy": {"candidates": ["cheap-a", "cheap-b", "strong-c"]},
    }
    body.update(extra)
    response = client.post("/arbitrations", json=body, headers=CLIENT)
    assert response.status_code == 201, response.text
    return response.json()["arbitration_id"]


def test_pedido_sem_token_e_401(client: TestClient) -> None:
    response = client.post("/arbitrations", json={})
    assert response.status_code == 401


def test_papel_invalido_e_401(client: TestClient) -> None:
    response = client.get("/metrics", headers={"Authorization": "Bearer nope"})
    assert response.status_code == 401


def test_pedido_valido_devolve_201_e_fica_concluido(client: TestClient) -> None:
    arbitration_id = _create(client, CASES[0]["text"])
    response = client.get(f"/arbitrations/{arbitration_id}", headers=CLIENT)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["spent_usd"] == pytest.approx(0.024)
    assert set(body["fields"]) == set(claim_output_schema()["properties"])
    assert body["fields"]["claimed_amount"]["decision"] == "accept"


def test_schema_invalido_e_422_e_nenhum_modelo_e_chamado(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        "arbitrationlab.api.routes.run_arbitration_job",
        lambda *args, **kwargs: calls.append("chamado"),
    )
    response = client.post(
        "/arbitrations",
        json={"task_id": "x", "text": "texto", "output_schema": {"type": 42}},
        headers=CLIENT,
    )
    assert response.status_code == 422
    assert calls == []


@pytest.mark.parametrize(
    "body",
    [
        {"task_id": "x", "text": "t", "output_schema": {}, "extra": 1},
        {"task_id": "", "text": "t", "output_schema": {}},
        {"task_id": "x", "text": "", "output_schema": {}},
        {"task_id": "x", "text": "t", "output_schema": {}, "max_spend": -1},
        {"task_id": "x", "text": "t", "output_schema": {}, "policy": {"candidates": ["nope"]}},
        {"task_id": "x", "text": "t", "output_schema": {}, "policy": {"accept_threshold": 3}},
        {"task_id": "x", "text": "t", "output_schema": {}, "policy": {"verify_threshold": 0.9}},
    ],
)
def test_entradas_invalidas_sao_422(client: TestClient, body: dict[str, Any]) -> None:
    response = client.post("/arbitrations", json=body, headers=CLIENT)
    assert response.status_code == 422


def test_candidato_fora_do_pool_e_422(client: TestClient) -> None:
    body = {"task_id": "x", "text": "t", "output_schema": {}, "policy": {"candidates": ["x-1"]}}
    response = client.post("/arbitrations", json=body, headers=CLIENT)
    assert response.status_code == 422


def test_arbitragem_inexistente_e_404_e_id_mal_formado_e_422(client: TestClient) -> None:
    assert client.get("/arbitrations/" + "a" * 32, headers=CLIENT).status_code == 404
    assert client.get("/arbitrations/abc", headers=CLIENT).status_code == 422


def test_schema_de_sinistro_e_servido_pela_api(client: TestClient) -> None:
    response = client.get("/schemas/claim", headers=CLIENT)
    assert response.status_code == 200
    assert response.json() == claim_output_schema()
    assert client.get("/schemas/claim").status_code == 401


def test_candidatos_devolvem_custo_latencia_e_estado(client: TestClient) -> None:
    arbitration_id = _create(client, CASES[0]["text"])
    response = client.get(f"/arbitrations/{arbitration_id}/candidates", headers=CLIENT)
    assert response.status_code == 200
    candidates = response.json()["candidates"]
    assert [c["model"] for c in candidates] == ["cheap-a", "cheap-b", "strong-c"]
    assert all(c["status"] == "ok" and c["cost_usd"] > 0 for c in candidates)
    assert all("latency_ms" in c for c in candidates)


def test_injeccao_fica_marcada_no_resultado(client: TestClient) -> None:
    injected = next(c for c in CASES if c["difficulty"] == "injection")
    arbitration_id = _create(client, injected["text"])
    body = client.get(f"/arbitrations/{arbitration_id}", headers=CLIENT).json()
    assert body["suspected_injection"] is True
    assert body["fields"]["claimed_amount"]["value"] != 50000


def test_falha_do_motor_fica_registada_sem_derrubar_a_api(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("motor avariado")

    monkeypatch.setattr("arbitrationlab.api.jobs.arbitrate_sync", boom)
    arbitration_id = _create(client, CASES[0]["text"])
    body = client.get(f"/arbitrations/{arbitration_id}", headers=CLIENT).json()
    assert body["status"] == "failed"
    assert "motor avariado" in body["error"]


def _ambiguous_case() -> dict[str, Any]:
    return next(c for c in CASES if c["difficulty"] == "ambiguous_date")


def test_revisao_com_papel_client_e_403(client: TestClient) -> None:
    arbitration_id = _create(client, _ambiguous_case()["text"])
    response = client.post(
        f"/arbitrations/{arbitration_id}/human-review",
        json={"decisions": [{"field": "incident_date", "action": "confirm"}]},
        headers={**CLIENT, "X-Actor": "alguem"},
    )
    assert response.status_code == 403


def test_revisao_sem_identificacao_do_revisor_e_422(client: TestClient) -> None:
    arbitration_id = _create(client, _ambiguous_case()["text"])
    response = client.post(
        f"/arbitrations/{arbitration_id}/human-review",
        json={"decisions": [{"field": "incident_date", "action": "confirm"}]},
        headers={"Authorization": f"Bearer {DEMO_REVIEWER_TOKEN}"},
    )
    assert response.status_code == 422


def test_correccao_humana_fica_auditada_e_uma_segunda_revisao_e_409(client: TestClient) -> None:
    case = _ambiguous_case()
    arbitration_id = _create(client, case["text"])
    before = client.get(f"/arbitrations/{arbitration_id}", headers=CLIENT).json()
    assert before["fields"]["incident_date"]["pending_review"] is True
    assert before["pending_review"] == ["incident_date"]

    response = client.post(
        f"/arbitrations/{arbitration_id}/human-review",
        json={
            "decisions": [
                {
                    "field": "incident_date",
                    "action": "correct",
                    "value": case["gold"]["incident_date"],
                }
            ]
        },
        headers=REVIEWER,
    )
    assert response.status_code == 200, response.text
    field = response.json()["fields"]["incident_date"]
    assert field["human_status"] == "accepted_by_human"
    assert field["value"] == case["gold"]["incident_date"]
    assert response.json()["pending_review"] == []

    again = client.post(
        f"/arbitrations/{arbitration_id}/human-review",
        json={"decisions": [{"field": "incident_date", "action": "confirm"}]},
        headers=REVIEWER,
    )
    assert again.status_code == 409


def test_correccao_invalida_e_422_e_nao_altera_o_campo(client: TestClient) -> None:
    arbitration_id = _create(client, _ambiguous_case()["text"])
    response = client.post(
        f"/arbitrations/{arbitration_id}/human-review",
        json={
            "decisions": [{"field": "incident_date", "action": "correct", "value": "31/02/2026"}]
        },
        headers=REVIEWER,
    )
    assert response.status_code == 422
    body = client.get(f"/arbitrations/{arbitration_id}", headers=CLIENT).json()
    assert body["fields"]["incident_date"]["human_status"] is None


def test_correccao_sem_valor_e_422_e_campo_inexistente_e_422(client: TestClient) -> None:
    arbitration_id = _create(client, _ambiguous_case()["text"])
    no_value = client.post(
        f"/arbitrations/{arbitration_id}/human-review",
        json={"decisions": [{"field": "incident_date", "action": "correct"}]},
        headers=REVIEWER,
    )
    unknown = client.post(
        f"/arbitrations/{arbitration_id}/human-review",
        json={"decisions": [{"field": "nao_existe", "action": "confirm"}]},
        headers=REVIEWER,
    )
    assert no_value.status_code == 422
    assert unknown.status_code == 422


def test_metricas_e_exportacao_reflectem_as_revisoes(client: TestClient) -> None:
    case = _ambiguous_case()
    arbitration_id = _create(client, case["text"])
    client.post(
        f"/arbitrations/{arbitration_id}/human-review",
        json={
            "decisions": [
                {
                    "field": "incident_date",
                    "action": "correct",
                    "value": case["gold"]["incident_date"],
                }
            ]
        },
        headers=REVIEWER,
    )
    metrics = client.get("/metrics", headers=CLIENT).json()
    assert metrics["reviews"] == 1
    assert metrics["provider"] == "mock"
    assert metrics["arbitrations"]["completed"] >= 1

    export = client.get("/reviews/export", headers=REVIEWER)
    assert export.status_code == 200
    lines = [json.loads(line) for line in export.text.splitlines()]
    assert len(lines) == 1
    assert lines[0]["source"] == "human_review"
    assert lines[0]["gold"] == {"incident_date": case["gold"]["incident_date"]}
    assert client.get("/reviews/export", headers=CLIENT).status_code == 403
