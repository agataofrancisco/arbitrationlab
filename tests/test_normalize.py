"""Normalizacao por tipo: datas (com ambiguidade), montantes, matriculas, moedas, booleanos."""

import math
from typing import Any

import pytest

from arbitrationlab.normalize import PARSERS, normalize


@pytest.mark.parametrize(
    ("raw", "value"),
    [
        ("2026-02-03", "2026-02-03"),
        ("3 de fevereiro de 2026", "2026-02-03"),
        ("18/02/2026", "2026-02-18"),
        ("02/18/2026", "2026-02-18"),
        ("15.03.2026", "2026-03-15"),
        ("05-05-2026", "2026-05-05"),
    ],
)
def test_datas_inequivocas_normalizam(raw: str, value: str) -> None:
    result = normalize("date", raw)
    assert result.status == "ok"
    assert result.value == value


def test_data_ambigua_nao_escolhe_leitura() -> None:
    result = normalize("date", "3/2/2026")
    assert result.status == "ambiguous"
    assert result.value is None
    assert result.options == ("2026-02-03", "2026-03-02")


@pytest.mark.parametrize("raw", ["31/02/2026", "13/13/2026", "3/2/1700", "ontem", "2026/02"])
def test_datas_invalidas_sao_nao_normalizaveis(raw: str) -> None:
    assert normalize("date", raw).status == "unparseable"


@pytest.mark.parametrize(
    ("raw", "value"),
    [
        ("1.250,50 €", 1250.5),
        ("1,250.50", 1250.5),
        ("1250.5", 1250.5),
        ("1.250", 1250.0),
        ("1250 EUR", 1250.0),
        ("1.250,50 euros", 1250.5),
        (1250.5, 1250.5),
    ],
)
def test_montantes_numericos(raw: Any, value: float) -> None:
    result = normalize("amount", raw)
    assert result.ok
    assert result.value == pytest.approx(value)


@pytest.mark.parametrize(
    ("raw", "value"),
    [
        ("mil duzentos e cinquenta euros e cinquenta cêntimos", 1250.5),
        ("oito mil e oitocentos e quarenta e seis euros e oitenta e nove cêntimos", 8846.89),
        ("zero euros", 0.0),
        ("um euro", 1.0),
        ("vinte e cinco", 25.0),
    ],
)
def test_montantes_por_extenso(raw: str, value: float) -> None:
    result = normalize("amount", raw)
    assert result.ok
    assert result.value == pytest.approx(value)


@pytest.mark.parametrize("raw", [-3, True, math.nan, math.inf, "abc", "cinco euros e", "1,2,3x"])
def test_montantes_invalidos(raw: Any) -> None:
    assert normalize("amount", raw).status == "unparseable"


@pytest.mark.parametrize(
    ("raw", "value"),
    [
        ("aa-12-bc", "AA12BC"),
        ("12 AB 34", "12AB34"),
        ("AA.12.BC", "AA12BC"),
        ("ab 12 cd", "AB12CD"),
    ],
)
def test_matriculas_canonicas(raw: str, value: str) -> None:
    result = normalize("plate", raw)
    assert result.ok and result.value == value


@pytest.mark.parametrize("raw", ["XX", "AMANHA", "AA-12", "1234567"])
def test_matriculas_invalidas(raw: str) -> None:
    assert normalize("plate", raw).status == "unparseable"


@pytest.mark.parametrize(
    ("raw", "value"),
    [("€", "EUR"), ("euros", "EUR"), ("USD", "USD"), ("US$", "USD"), ("£", "GBP")],
)
def test_moedas(raw: str, value: str) -> None:
    assert normalize("currency", raw).value == value


def test_moeda_desconhecida() -> None:
    assert normalize("currency", "BRL").status == "unparseable"


@pytest.mark.parametrize(
    ("raw", "value"), [("Sim", True), ("não", False), ("nao", False), (True, True), (False, False)]
)
def test_booleanos(raw: Any, value: bool) -> None:
    result = normalize("bool", raw)
    assert result.ok and result.value is value


def test_booleano_com_valor_estranho_nao_normaliza() -> None:
    assert normalize("bool", 1).status == "unparseable"
    assert normalize("bool", None).status == "missing"


def test_apolice_canonica() -> None:
    result = normalize("id", "ha 2026 004521")
    assert result.ok and result.value == "HA-2026-004521"


def test_vazio_e_missing() -> None:
    for kind in PARSERS:
        assert normalize(kind, None).status == "missing"
        assert normalize(kind, "   ").status == "missing"


def test_tipo_desconhecido_trata_se_como_texto() -> None:
    result = normalize("nao-existe", "  olá  ")
    assert result.ok and result.value == "olá"


@pytest.mark.parametrize("kind", sorted(PARSERS))
def test_valores_inesperados_nunca_lancam_excepcao(kind: str) -> None:
    weird: list[Any] = [[1, 2], {"a": 1}, b"bytes", 3.5, object(), (), 0, False, "\x00"]
    for raw in weird:
        result = normalize(kind, raw)
        assert result.status in {"ok", "missing", "unparseable", "ambiguous"}
