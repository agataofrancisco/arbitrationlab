"""Plegagem de texto (minusculas e sem acentos) que preserva os offsets.

Cada caractere e substituido por exactamente um caractere, por isso um indice no texto
plegado corresponde ao mesmo indice no texto original.
"""

from __future__ import annotations

import unicodedata


def fold_char(char: str) -> str:
    """Devolve a versao minuscula sem acento de um caractere (sempre um caractere)."""
    lowered = char.lower()
    decomposed = unicodedata.normalize("NFD", lowered)
    base = [c for c in decomposed if not unicodedata.combining(c)]
    if not base:
        return lowered
    return base[0]


def fold_text(text: str) -> str:
    """Plegagem de texto com o mesmo comprimento do original. Aceita so str."""
    if not isinstance(text, str):
        raise TypeError("fold_text espera uma string")
    return "".join(fold_char(c) for c in text)


def fold_key(value: str) -> str:
    """Forma plegada e sem espacos repetidos, para comparar rotulos e palavras."""
    return " ".join(fold_text(value).split())
