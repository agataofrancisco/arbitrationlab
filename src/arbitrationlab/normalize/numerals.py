"""Numerais em portugues (0 a 999 999) para gerar e ler montantes por extenso.

Os tokens de entrada devem estar em minusculas e sem acentos (ver `normalize.text`).
"""

from __future__ import annotations

UNITS: dict[str, int] = {
    "zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4,
    "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10, "onze": 11,
    "doze": 12, "treze": 13, "catorze": 14, "quatorze": 14, "quinze": 15,
    "dezasseis": 16, "dezesseis": 16, "dezassete": 17, "dezessete": 17, "dezoito": 18,
    "dezanove": 19, "dezenove": 19,
}  # fmt: skip
TENS: dict[str, int] = {
    "vinte": 20, "trinta": 30, "quarenta": 40, "cinquenta": 50, "sessenta": 60,
    "setenta": 70, "oitenta": 80, "noventa": 90,
}  # fmt: skip
HUNDREDS: dict[str, int] = {
    "cem": 100, "cento": 100, "duzentos": 200, "duzentas": 200, "trezentos": 300,
    "trezentas": 300, "quatrocentos": 400, "quatrocentas": 400, "quinhentos": 500,
    "quinhentas": 500, "seiscentos": 600, "seiscentas": 600, "setecentos": 700,
    "setecentas": 700, "oitocentos": 800, "oitocentas": 800, "novecentos": 900,
    "novecentas": 900,
}  # fmt: skip

_UNIT_WORDS = {0: "zero", 1: "um", 2: "dois", 3: "tres", 4: "quatro", 5: "cinco", 6: "seis",
               7: "sete", 8: "oito", 9: "nove", 10: "dez", 11: "onze", 12: "doze",
               13: "treze", 14: "catorze", 15: "quinze", 16: "dezasseis", 17: "dezassete",
               18: "dezoito", 19: "dezanove"}  # fmt: skip
_TEN_WORDS = {v: k for k, v in TENS.items()}
_HUNDRED_WORDS = {100: "cem", 200: "duzentos", 300: "trezentos", 400: "quatrocentos",
                  500: "quinhentos", 600: "seiscentos", 700: "setecentos", 800: "oitocentos",
                  900: "novecentos"}  # fmt: skip

NUMBER_WORDS: frozenset[str] = frozenset({*UNITS, *TENS, *HUNDREDS, "mil"})


def _under_100(n: int) -> str:
    if n < 20:
        return _UNIT_WORDS[n]
    tens, unit = divmod(n, 10)
    return _TEN_WORDS[tens * 10] if unit == 0 else f"{_TEN_WORDS[tens * 10]} e {_UNIT_WORDS[unit]}"


def _under_1000(n: int) -> str:
    if n < 100:
        return _under_100(n)
    hundreds, rest = divmod(n, 100)
    head = "cem" if n == 100 else _HUNDRED_WORDS[hundreds * 100]
    return head if rest == 0 else f"{head} e {_under_100(rest)}"


def int_to_words_pt(n: int) -> str:
    """Escreve um inteiro entre 0 e 999 999 em portugues."""
    if not isinstance(n, int) or isinstance(n, bool) or not 0 <= n <= 999_999:
        raise ValueError("int_to_words_pt aceita inteiros entre 0 e 999999")
    if n == 0:
        return "zero"
    thousands, rest = divmod(n, 1000)
    parts: list[str] = []
    if thousands:
        parts.append("mil" if thousands == 1 else f"{_under_1000(thousands)} mil")
    if rest:
        parts.append(_under_1000(rest))
    return " e ".join(parts)


def words_to_int(tokens: list[str]) -> int:
    """Le uma sequencia de tokens numericos (sem acentos) e devolve o inteiro.

    Lanca ValueError para tokens desconhecidos ou sequencias vazias.
    """
    if not tokens:
        raise ValueError("sequencia numerica vazia")
    total = 0
    current = 0
    for word in tokens:
        if word == "e":
            continue
        if word in UNITS:
            current += UNITS[word]
        elif word in TENS:
            current += TENS[word]
        elif word in HUNDREDS:
            current += HUNDREDS[word]
        elif word == "mil":
            total += (current or 1) * 1000
            current = 0
        else:
            raise ValueError(f"palavra numerica desconhecida: {word!r}")
    return total + current
