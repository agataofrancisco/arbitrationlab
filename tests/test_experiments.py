"""Experiencia em mock: metricas com casos conhecidos, relatorio gerado pela run e determinismo."""

import json
from pathlib import Path
from typing import Any

import pytest

from arbitrationlab.experiments.metrics import (
    coverage,
    critical_error_rate,
    exact_match,
    field_scores,
    summarize,
)
from arbitrationlab.experiments.run import run_experiment
from arbitrationlab.experiments.strategies import STRATEGIES, CaseResult
from arbitrationlab.schema import CLAIM_FIELDS

GOLD: dict[str, Any] = {
    "policy_number": "HA-2026-004521",
    "incident_date": "2026-02-18",
    "license_plate": "AA12BC",
    "claimed_amount": 1250.5,
    "currency": "EUR",
    "third_party_involved": True,
    "injuries_reported": None,
}


def _result(final: dict[str, Any], decisions: dict[str, str] | None = None) -> CaseResult:
    return CaseResult(
        strategy="x",
        case_id="CLM-T",
        difficulty="clean",
        final={**GOLD, **final},
        gold=GOLD,
        model_cost=0.01,
        review_cost=0.0,
        n_reviewed=0,
        latency_ms=1.0,
        decisions=decisions or {},
    )


def test_resultado_perfeito_tem_f1_1_e_exact_match_1() -> None:
    results = [_result({})]
    assert exact_match(results) == 1.0
    assert coverage(results) == pytest.approx(6 / 7)
    assert critical_error_rate(results) == 0.0
    assert all(
        s["f1"] == 1.0 for name, s in field_scores(results).items() if GOLD[name] is not None
    )


def test_valor_aceite_errado_conta_como_erro_critico_e_fp() -> None:
    results = [_result({"claimed_amount": 1520.0})]
    assert critical_error_rate(results) == pytest.approx(1 / 7)
    scores = field_scores(results)
    assert scores["claimed_amount"]["fp"] == 1
    assert scores["claimed_amount"]["fn"] == 1
    assert exact_match(results) == 0.0


def test_abstencao_em_campo_com_gold_nulo_nao_e_erro() -> None:
    results = [_result({"injuries_reported": None})]
    assert critical_error_rate(results) == 0.0
    assert exact_match(results) == 1.0


def test_aceitar_valor_quando_o_gold_e_nulo_e_erro_critico() -> None:
    results = [_result({"injuries_reported": True})]
    assert critical_error_rate(results) == pytest.approx(1 / 7)
    assert exact_match(results) == 0.0


def test_resumo_inclui_todas_as_metricas_pedidas() -> None:
    summary = summarize([_result({})])
    for key in (
        "exact_match",
        "macro_f1",
        "coverage",
        "critical_error_rate",
        "review_rate",
        "mean_cost_usd",
        "mean_latency_ms",
        "exact_match_by_difficulty",
    ):
        assert key in summary
    assert set(summary["field_f1"]) == set(CLAIM_FIELDS)


@pytest.fixture(scope="module")
def experiment(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    out = tmp_path_factory.mktemp("exp")
    payload = run_experiment(out_dir=out, review_cost_usd=0.30)
    payload["_out"] = out
    return payload


def test_run_gera_tabela_grafico_e_provider_mock(experiment: dict[str, Any]) -> None:
    out: Path = experiment["_out"]
    report = (out / "mock-report.md").read_text(encoding="utf-8")
    assert "provider: mock" in report
    for label in (
        "modelo barato único",
        "modelo forte único",
        "voto maioritário",
        "arbitragem por evidência",
        "arbitragem + revisão",
    ):
        assert label in report
    assert (out / "mock-accuracy-vs-cost.png").stat().st_size > 0
    data = json.loads((out / "mock-results.json").read_text(encoding="utf-8"))
    assert data["meta"]["provider"] == "mock"
    assert data["meta"]["n_evaluation"] == 72
    assert data["meta"]["calibrator"]["fitted"] is True


def test_metricas_estao_em_intervalo_valido(experiment: dict[str, Any]) -> None:
    for strategy in STRATEGIES:
        s = experiment["summaries"][strategy]
        for key in ("exact_match", "macro_f1", "coverage", "critical_error_rate", "review_rate"):
            assert 0.0 <= s[key] <= 1.0, (strategy, key)


def test_revisao_so_existe_na_estrategia_com_revisao(experiment: dict[str, Any]) -> None:
    for strategy in STRATEGIES:
        if strategy == "arbitration_review":
            assert experiment["summaries"][strategy]["review_rate"] > 0
        else:
            assert experiment["summaries"][strategy]["review_rate"] == 0.0


def test_erros_correlacionados_somam_apanhados_e_escapados(experiment: dict[str, Any]) -> None:
    corr = experiment["analysis"]["correlated_dates"]
    assert corr["total"] == corr["caught"] + corr["escaped"]


def test_sensibilidade_cresce_com_o_custo_de_revisao(experiment: dict[str, Any]) -> None:
    costs = [row["mean_cost_usd"] for row in experiment["analysis"]["sensitivity"]]
    assert costs == sorted(costs) and costs[0] < costs[-1]


def test_run_e_deterministica_nas_metricas(tmp_path: Path, experiment: dict[str, Any]) -> None:
    again = run_experiment(out_dir=tmp_path, review_cost_usd=0.30)
    assert again["summaries"]["arbitration_review"]["exact_match"] == pytest.approx(
        experiment["summaries"]["arbitration_review"]["exact_match"]
    )
    assert again["analysis"]["correlated_dates"] == experiment["analysis"]["correlated_dates"]
    assert again["analysis"]["accepted_wrong"] == experiment["analysis"]["accepted_wrong"]
