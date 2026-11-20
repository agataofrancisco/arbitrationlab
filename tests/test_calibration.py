"""Calibracao: fiabilidade Beta, score logistico e ECE em dados de calibracao conhecida."""

import pytest

from arbitrationlab.calibration import (
    ConfidenceModel,
    ReliabilityTable,
    expected_calibration_error,
    reliability_bins,
)


def test_fiabilidade_comeca_no_prior_e_actualiza_com_os_acertos() -> None:
    table = ReliabilityTable()
    assert table.mean("modelo", "incident_date") == pytest.approx(0.5)
    table.observe_many(
        [("modelo", "incident_date", True)] * 3 + [("modelo", "incident_date", False)]
    )
    assert table.counts("modelo", "incident_date") == (3, 1)
    assert table.mean("modelo", "incident_date") == pytest.approx(4 / 6)
    assert table.mean("outro", "incident_date") == pytest.approx(0.5)


def test_prior_beta_invalido_e_rejeitado() -> None:
    with pytest.raises(ValueError):
        ReliabilityTable(alpha0=0)


def test_ece_zero_para_confianca_bem_calibrada() -> None:
    # Em cada intervalo, a taxa de acerto e exactamente a confianca media.
    confidences: list[float] = []
    outcomes: list[int] = []
    for step in range(10):
        p = step / 10 + 0.05
        hits = round(p * 100)
        confidences.extend([p] * 100)
        outcomes.extend([1] * hits + [0] * (100 - hits))
    assert expected_calibration_error(confidences, outcomes) == pytest.approx(0.0, abs=1e-9)


def test_ece_alto_para_confianca_excessiva() -> None:
    assert expected_calibration_error([0.9] * 10, [1] * 5 + [0] * 5) == pytest.approx(0.4)


def test_ece_vazio_e_zero_e_erros_de_entrada() -> None:
    assert expected_calibration_error([], []) == 0.0
    with pytest.raises(ValueError):
        expected_calibration_error([1.5], [1])
    with pytest.raises(ValueError):
        reliability_bins([0.5], [1, 0])


def test_diagrama_de_fiabilidade_soma_as_contagens() -> None:
    bins = reliability_bins([0.05, 0.55, 0.56, 1.0], [0, 1, 1, 1], n_bins=10)
    assert sum(b["count"] for b in bins) == 4
    assert bins[9]["count"] == 1  # 1.0 cai no ultimo intervalo
    assert bins[5]["accuracy"] == pytest.approx(1.0)


def test_score_por_omissao_cresce_com_acordo_e_evidencia() -> None:
    model = ConfidenceModel()
    low = model.predict((1 / 3, 0.0, 0.5))
    mid = model.predict((1 / 3, 1.0, 0.5))
    high = model.predict((1.0, 1.0, 0.8))
    assert low < mid < high
    assert not model.fitted


def test_regressao_logistica_aprende_a_separar_os_casos() -> None:
    features = [[1.0, 1.0, 0.9]] * 20 + [[0.33, 0.0, 0.4]] * 20
    outcomes = [1] * 20 + [0] * 20
    model = ConfidenceModel()
    model.fit(features, outcomes)
    assert model.fitted and model.n_train == 40
    assert model.predict((1.0, 1.0, 0.9)) > 0.8
    assert model.predict((0.33, 0.0, 0.4)) < 0.2


def test_regressao_com_uma_so_classe_mantem_a_taxa_observada() -> None:
    model = ConfidenceModel()
    model.fit([[1.0, 1.0, 0.5]] * 4, [1, 1, 1, 1])
    assert model.predict((0.0, 0.0, 0.0)) > 0.9


def test_fit_valida_entradas() -> None:
    model = ConfidenceModel()
    with pytest.raises(ValueError):
        model.fit([], [])
    with pytest.raises(ValueError):
        model.fit([[1.0, 1.0]], [1])
