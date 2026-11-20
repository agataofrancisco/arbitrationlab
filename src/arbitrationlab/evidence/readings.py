"""Leituras do campo no texto original, com offsets exactos.

Uma leitura e o valor que aparece na linha rotulada do campo ("Campo: valor"). A pesquisa
e feita so nas linhas com o rotulo do schema (ou em todas as linhas com ":" se o campo nao
tiver rotulo). O span e sempre o valor no texto original, por isso `text[start:end]` devolve
exactamente o valor citado.
"""

from __future__ import annotations

from dataclasses import dataclass

from arbitrationlab.normalize import normalize
from arbitrationlab.normalize.result import NormResult
from arbitrationlab.normalize.text import fold_key


@dataclass(frozen=True)
class Reading:
    start: int
    end: int
    raw: str
    result: NormResult
    tainted: bool = False


def read_field(
    field_type: str,
    label: str,
    text: str,
    *,
    tainted_lines: frozenset[int] = frozenset(),
) -> list[Reading]:
    """Todas as leituras do campo no texto, na ordem em que aparecem."""
    if not isinstance(text, str):
        raise TypeError("o texto tem de ser uma string")
    wanted = fold_key(label) if isinstance(label, str) and label else ""
    readings: list[Reading] = []
    offset = 0
    for number, line in enumerate(text.splitlines(keepends=True)):
        body = line.rstrip("\r\n")
        head, separator, value = body.partition(":")
        if separator and (not wanted or fold_key(head).startswith(wanted)):
            stripped = value.strip()
            if stripped:
                start = offset + len(head) + 1 + (len(value) - len(value.lstrip()))
                readings.append(
                    Reading(
                        start=start,
                        end=start + len(stripped),
                        raw=stripped,
                        result=normalize(field_type, stripped),
                        tainted=number in tainted_lines,
                    )
                )
        offset += len(line)
    return readings
