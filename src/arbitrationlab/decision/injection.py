"""Deteccao de instrucoes escondidas no texto da participacao.

O texto e dados. Uma linha com aspecto de instrucao (por exemplo "Nota do sistema: define ...")
nao muda a politica nem os campos pedidos. Essa linha fica marcada: os valores que aparecem
nela nao contam como evidencia, e o caso recebe a flag `suspected_injection`.
"""

from __future__ import annotations

import re

from arbitrationlab.normalize.text import fold_text

INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"nota do sistema\s*:"),
    re.compile(r"\bsistema\s*:"),
    re.compile(r"\bsystem\s*:"),
    re.compile(r"ignora (?:as )?instrucoes"),
    re.compile(r"ignore (?:all |previous |the )?(?:instructions|previous)"),
    re.compile(r"\bdefine\s+\w+\s+como\b"),
    re.compile(r"\bmarca(?:r)?\s+(?:como\s+)?aceite\b"),
    re.compile(r"\baprova\s+(?:o|a)\s+valor\b"),
)


def detect_injection_lines(text: str) -> frozenset[int]:
    """Numeros (a partir de 0) das linhas que contem padroes de instrucao."""
    if not isinstance(text, str):
        raise TypeError("o texto tem de ser uma string")
    flagged: set[int] = set()
    for number, line in enumerate(text.splitlines()):
        folded = fold_text(line)
        if any(pattern.search(folded) for pattern in INJECTION_PATTERNS):
            flagged.add(number)
    return frozenset(flagged)
