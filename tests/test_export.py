"""Exportacao de revisoes para JSONL golden: so etiquetas confirmadas ou corrigidas."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from arbitrationlab.api.app import create_app
from arbitrationlab.config import DEMO_CLIENT_TOKEN, Settings
from arbitrationlab.dataset.validate import load_jsonl
from arbitrationlab.export import export_reviews_jsonl
from arbitrationlab.schema import claim_output_schema
from arbitrationlab.store.repository import ArbitrationStore, Decision

ROOT = Path(__file__).resolve().parents[1]
CASES = load_jsonl(ROOT / "datasets" / "claims" / "claims.jsonl")
CLIENT = {"Authorization": f"Bearer {DEMO_CLIENT_TOKEN}"}


def _store_with_reviews(tmp_path: Path) -> ArbitrationStore:
    settings = Settings(database_url=f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    client = TestClient(create_app(settings))
    ambiguous = next(c for c in CASES if c["difficulty"] == "ambiguous_date")
    body = {
        "task_id": "t",
        "text": ambiguous["text"],
        "output_schema": claim_output_schema(),
        "policy": {"candidates": ["cheap-a", "cheap-b", "strong-c"]},
    }
    arbitration_id = client.post("/arbitrations", json=body, headers=CLIENT).json()[
        "arbitration_id"
    ]
    store = client.app.state.store
    store.review(
        arbitration_id,
        "revisor.joao",
        [
            Decision("incident_date", "correct", ambiguous["gold"]["incident_date"]),
        ],
    )
    return store


def test_exportacao_marca_source_human_review_e_tem_gold_do_campo(tmp_path: Path) -> None:
    store = _store_with_reviews(tmp_path)
    lines = [json.loads(x) for x in export_reviews_jsonl(store).splitlines()]
    assert len(lines) == 1
    record = lines[0]
    assert record["source"] == "human_review"
    assert list(record["gold"]) == ["incident_date"]
    assert record["reviewed_by"] == "revisor.joao"
    assert record["text"].startswith("Participação")


def test_unreadable_nao_entra_como_etiqueta(tmp_path: Path) -> None:
    settings = Settings(database_url=f"sqlite:///{(tmp_path / 'ilegivel.db').as_posix()}")
    client = TestClient(create_app(settings))
    ambiguous = next(c for c in CASES if c["difficulty"] == "ambiguous_date")
    body = {
        "task_id": "t",
        "text": ambiguous["text"],
        "output_schema": claim_output_schema(),
        "policy": {"candidates": ["cheap-a", "cheap-b", "strong-c"]},
    }
    arbitration_id = client.post("/arbitrations", json=body, headers=CLIENT).json()[
        "arbitration_id"
    ]
    store = client.app.state.store
    store.review(arbitration_id, "revisor.joao", [Decision("incident_date", "unreadable")])
    assert export_reviews_jsonl(store) == ""


def test_exportacao_vazia_e_string_vazia(tmp_path: Path) -> None:
    settings = Settings(database_url=f"sqlite:///{(tmp_path / 'vazio.db').as_posix()}")
    store = ArbitrationStore(settings.database_url)
    assert export_reviews_jsonl(store) == ""
