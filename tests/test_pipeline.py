"""Pipeline ponta a ponta sobre o dataset: evidencia, orcamento, erro correlacionado e entradas."""

import json
from pathlib import Path
from typing import Any

import pytest

from arbitrationlab.decision import Policy
from arbitrationlab.generation.registry import (
    CHEAP_A,
    CHEAP_B,
    STRONG_C,
    VERIFIER,
    default_mock_models,
)
from arbitrationlab.normalize import normalize
from arbitrationlab.pipeline import arbitrate_sync, select_candidates
from arbitrationlab.schema import claim_output_schema

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    json.loads(line)
    for line in (ROOT / "datasets" / "claims" / "claims.jsonl")
    .read_text(encoding="utf-8")
    .splitlines()
]


def _run(text: str, policy: Policy, names: tuple[str, ...] = (CHEAP_A, CHEAP_B, STRONG_C)) -> Any:
    models = default_mock_models()
    return arbitrate_sync(
        text,
        claim_output_schema(),
        [models[n] for n in names],
        policy=policy,
        verifier=models[VERIFIER],
    )


def test_cada_valor_aceite_tem_evidencia_no_texto() -> None:
    policy = Policy(max_spend=1.0, timeout_s=2)
    for case in CASES[:40]:
        outcome = _run(case["text"], policy)
        for name, verdict in outcome.verdicts.items():
            if verdict.decision == "accept":
                assert verdict.evidence.score > 0, (case["id"], name)


def test_casos_limpos_aceitam_exactamente_o_gold() -> None:
    policy = Policy(max_spend=1.0, timeout_s=2)
    clean = [c for c in CASES if c["difficulty"] == "clean"]
    for case in clean:
        outcome = _run(case["text"], policy)
        for name, value in outcome.accepted_values().items():
            if value is not None:
                expected = case["gold"][name]
                if isinstance(expected, float):
                    assert value == pytest.approx(expected), (case["id"], name)
                else:
                    assert value == expected, (case["id"], name)


def test_erro_correlacionado_de_data_nao_e_aceite() -> None:
    policy = Policy(max_spend=1.0, timeout_s=2)
    checked = 0
    for case in CASES:
        if case["difficulty"] != "ambiguous_date":
            continue
        outcome = _run(case["text"], policy, (CHEAP_A, CHEAP_B))
        gold = case["gold"]["incident_date"]
        wrong = [
            normalize("date", r.output["incident_date"]).value != gold for r in outcome.candidates
        ]
        if all(wrong):
            checked += 1
            verdict = outcome.verdicts["incident_date"]
            assert verdict.decision != "accept", case["id"]
            assert verdict.accepted_value is None
    assert checked >= 1, "o dataset tem de incluir pelo menos um erro correlacionado"


def test_data_aceite_com_evidencia_bate_sempre_com_o_gold_nos_casos_limpos() -> None:
    policy = Policy(max_spend=1.0, timeout_s=2)
    for case in [c for c in CASES if c["difficulty"] == "date_words"]:
        outcome = _run(case["text"], policy)
        verdict = outcome.verdicts["incident_date"]
        if verdict.decision == "accept":
            assert verdict.accepted_value == case["gold"]["incident_date"], case["id"]


def test_orcamento_insuficiente_omite_o_terceiro_candidato() -> None:
    text = CASES[0]["text"]
    outcome = _run(text, Policy(max_spend=0.005, timeout_s=2))
    statuses = [r.status for r in outcome.candidates]
    assert statuses == ["ok", "ok", "skipped"]
    assert outcome.candidates[2].reason == "skipped: budget"
    assert outcome.spent_usd <= 0.005 + 1e-9


def test_gasto_nunca_excede_max_spend() -> None:
    outcome = _run(CASES[0]["text"], Policy(max_spend=0.03, timeout_s=2))
    assert outcome.spent_usd <= 0.03 + 1e-9


def test_selecao_de_candidatos_por_nome_e_validada() -> None:
    models = list(default_mock_models().values())
    chosen = select_candidates(models, (CHEAP_B, CHEAP_A))
    assert [p.name for p in chosen] == [CHEAP_B, CHEAP_A]
    with pytest.raises(ValueError, match="desconhecidos"):
        select_candidates(models, ("nao-existe",))


def test_entradas_invalidas_sao_rejeitadas_antes_de_chamar_modelos() -> None:
    models = default_mock_models()
    with pytest.raises(ValueError):
        arbitrate_sync(
            "texto", {"type": 42}, [models[CHEAP_A]], policy=Policy(max_spend=1, timeout_s=2)
        )
    with pytest.raises(ValueError):
        arbitrate_sync(None, claim_output_schema(), [models[CHEAP_A]], policy=Policy(max_spend=1))  # type: ignore[arg-type]


def test_politica_invalida_e_rejeitada() -> None:
    with pytest.raises(ValueError):
        Policy(accept_threshold=0.3, verify_threshold=0.9)
    with pytest.raises(ValueError):
        Policy(max_spend=-1)
    with pytest.raises(ValueError):
        Policy(accept_threshold=1.5)
