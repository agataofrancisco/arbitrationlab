"""Numerais em portugues: ida e volta entre inteiros e palavras."""

import pytest

from arbitrationlab.normalize.numerals import int_to_words_pt, words_to_int


@pytest.mark.parametrize(
    ("number", "words"),
    [
        (0, "zero"),
        (7, "sete"),
        (16, "dezasseis"),
        (21, "vinte e um"),
        (100, "cem"),
        (250, "duzentos e cinquenta"),
        (1000, "mil"),
        (1250, "mil e duzentos e cinquenta"),
        (8846, "oito mil e oitocentos e quarenta e seis"),
    ],
)
def test_int_to_words_conhecidos(number: int, words: str) -> None:
    assert int_to_words_pt(number) == words


def test_ida_e_volta_para_o_intervalo_amostrado() -> None:
    for number in list(range(0, 1200)) + list(range(10_000, 999_999, 997)):
        assert words_to_int(int_to_words_pt(number).split()) == number


def test_palavras_desconhecidas_levantam_erro() -> None:
    with pytest.raises(ValueError):
        words_to_int(["mil", "bananas"])
    with pytest.raises(ValueError):
        words_to_int([])


@pytest.mark.parametrize("bad", [-1, 1_000_000, 1.5, True, "5"])
def test_int_to_words_rejeita_entradas_invalidas(bad: object) -> None:
    with pytest.raises(ValueError):
        int_to_words_pt(bad)  # type: ignore[arg-type]
