"""Schema de saida, validacao de candidatos e runner paralelo com timeout e orcamento."""

import asyncio
from typing import Any

import pytest

from arbitrationlab.generation.providers import ErrorProfile, MockProvider, ProviderError
from arbitrationlab.generation.registry import CHEAP_A, CHEAP_B, STRONG_C, default_mock_models
from arbitrationlab.generation.runner import BudgetLedger, generate_candidates
from arbitrationlab.schema import (
    CLAIM_FIELDS,
    claim_output_schema,
    validate_candidate_output,
    validate_output_schema,
)

TEXT = (
    "Apólice: HA-2026-004521\n"
    "Data do sinistro: 18/02/2026\n"
    "Matrícula: AA-12-BC\n"
    "Valor reclamado: 1.250,50 €\n"
    "Moeda: EUR\n"
    "Terceiro envolvido: sim\n"
    "Feridos: não\n"
)


def _three_models() -> list[Any]:
    models = default_mock_models()
    return [models[CHEAP_A], models[CHEAP_B], models[STRONG_C]]


def test_schema_de_sinistro_e_um_json_schema_valido() -> None:
    validate_output_schema(claim_output_schema())
    assert tuple(claim_output_schema()["required"]) == CLAIM_FIELDS


@pytest.mark.parametrize("bad", [{"type": 42}, "texto", None, {"properties": []}])
def test_schema_invalido_e_rejeitado(bad: Any) -> None:
    with pytest.raises(ValueError):
        validate_output_schema(bad)


def test_candidato_invalido_gera_erros_sem_lancar() -> None:
    schema = claim_output_schema()
    assert validate_candidate_output(schema, {"policy_number": 12345}) != []
    assert validate_candidate_output(schema, "nao e objecto") == ["a saida nao e um objecto JSON"]


def test_candidatos_paralelos_devolvem_um_registo_por_fornecedor() -> None:
    records = asyncio.run(
        generate_candidates(
            TEXT, claim_output_schema(), _three_models(), max_spend=0.05, timeout_s=2
        )
    )
    assert [r.model for r in records] == [CHEAP_A, CHEAP_B, STRONG_C]
    assert all(r.status == "ok" for r in records)
    assert records[2].output["claimed_amount"] == "1.250,50 €"


def test_fornecedor_que_excede_o_timeout_fica_timed_out() -> None:
    slow = MockProvider(
        "lento",
        parser="cheap",
        cost_per_call_usd=0.001,
        profile=ErrorProfile(kind="timeout", rate=1.0, latency_s=5),
    )
    fast = MockProvider("rapido", parser="strong", cost_per_call_usd=0.001)
    records = asyncio.run(
        generate_candidates(TEXT, claim_output_schema(), [slow, fast], max_spend=1, timeout_s=0.05)
    )
    assert records[0].status == "timed_out"
    assert records[1].status == "ok"


def test_orcamento_insuficiente_marca_skipped_budget() -> None:
    records = asyncio.run(
        generate_candidates(
            TEXT, claim_output_schema(), _three_models(), max_spend=0.005, timeout_s=2
        )
    )
    assert [r.status for r in records] == ["ok", "ok", "skipped"]
    assert records[2].reason == "skipped: budget"
    assert records[2].cost_usd == 0.0


def test_erro_do_fornecedor_nao_derruba_os_outros() -> None:
    broken = MockProvider(
        "avariado", parser="cheap", cost_per_call_usd=0.001, profile=ErrorProfile(kind="error")
    )
    ok = MockProvider("bom", parser="cheap", cost_per_call_usd=0.001)
    records = asyncio.run(
        generate_candidates(TEXT, claim_output_schema(), [broken, ok], max_spend=1, timeout_s=2)
    )
    assert records[0].status == "error"
    assert records[0].reason == "ProviderError"
    assert records[1].usable


def test_saida_invalida_do_mock_fica_invalid() -> None:
    bad = MockProvider(
        "mau",
        parser="cheap",
        cost_per_call_usd=0.001,
        profile=ErrorProfile(kind="bad_schema", rate=1.0),
    )
    records = asyncio.run(
        generate_candidates(TEXT, claim_output_schema(), [bad], max_spend=1, timeout_s=2)
    )
    assert records[0].status == "invalid"
    assert records[0].errors


def test_erro_correlacionado_produz_a_mesma_data_errada() -> None:
    models = default_mock_models()
    wrong_seen = 0
    for day in range(1, 13):
        for month in range(1, 13):
            if day == month:
                continue
            doc = f"Data do sinistro: {day:02d}/{month:02d}/2026\n"
            a = asyncio.run(models[CHEAP_A].extract(doc, claim_output_schema()))
            b = asyncio.run(models[CHEAP_B].extract(doc, claim_output_schema()))
            assert a["incident_date"] == b["incident_date"]
            if a["incident_date"] != f"2026-{month:02d}-{day:02d}":
                wrong_seen += 1
    # Com taxa de 15% e 132 documentos, o erro tem de aparecer e ser o mesmo nos dois modelos.
    assert wrong_seen > 0


def test_ledger_rejeita_valores_invalidos() -> None:
    with pytest.raises(ValueError):
        BudgetLedger(-1)
    with pytest.raises(ValueError):
        BudgetLedger(True)  # type: ignore[arg-type]


def test_entrada_nao_string_e_rejeitada() -> None:
    with pytest.raises(ValueError):
        asyncio.run(generate_candidates(None, {}, [], max_spend=1, timeout_s=1))  # type: ignore[arg-type]


def test_provider_error_e_excepcao_publica() -> None:
    assert issubclass(ProviderError, Exception)
