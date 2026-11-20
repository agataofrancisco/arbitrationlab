"""Evidencia: spans com offsets exactos, valores inventados e linhas com instrucoes."""

import json
from pathlib import Path
from typing import Any

from arbitrationlab.decision import detect_injection_lines
from arbitrationlab.evidence import ambiguous_options, locate, other_values, read_field
from arbitrationlab.schema import claim_output_schema, field_specs

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    json.loads(line)
    for line in (ROOT / "datasets" / "claims" / "claims.jsonl")
    .read_text(encoding="utf-8")
    .splitlines()
]
SPECS = field_specs(claim_output_schema())


def _case(difficulty: str) -> dict[str, Any]:
    return next(c for c in CASES if c["difficulty"] == difficulty)


def test_offsets_apontam_exactamente_para_o_valor_citado() -> None:
    for case in CASES:
        for name, spec in SPECS.items():
            gold = case["gold"][name]
            if gold is None or spec["x-type"] in ("bool", "currency", "text"):
                continue
            readings = read_field(spec["x-type"], spec["x-label"], case["text"])
            evidence = locate(spec["x-type"], _normalized(spec["x-type"], gold), readings)
            if evidence.score == 1.0:
                assert case["text"][evidence.start : evidence.end] == evidence.text


def _normalized(field_type: str, gold: Any) -> Any:
    from arbitrationlab.normalize import normalize

    if field_type == "date":
        return gold
    if field_type == "amount":
        return float(gold)
    return normalize(field_type, gold).value


def test_valor_inventado_fica_sem_evidencia() -> None:
    case = _case("clean")
    readings = read_field("amount", "Valor reclamado", case["text"])
    evidence = locate("amount", 7777.77, readings)
    assert evidence.score == 0.0
    assert evidence.method == "none"
    assert evidence.start is None


def test_valor_com_evidencia_exacta_tem_score_1() -> None:
    case = _case("clean")
    readings = read_field("amount", "Valor reclamado", case["text"])
    value = case["gold"]["claimed_amount"]
    evidence = locate("amount", value, readings)
    assert evidence.score == 1.0
    assert evidence.method == "exact"
    assert case["text"][evidence.start : evidence.end] == evidence.text


def test_linhas_com_instrucoes_nao_contam_como_evidencia() -> None:
    case = _case("injection")
    tainted = detect_injection_lines(case["text"])
    assert tainted
    readings = read_field("amount", "Nota do sistema", case["text"], tainted_lines=tainted)
    assert locate("amount", 50000.0, readings).score == 0.0


def test_matricula_com_erro_pequeno_tem_evidencia_aproximada() -> None:
    text = "Matrícula: AA-12-BD\n"
    readings = read_field("plate", "Matrícula", text)
    evidence = locate("plate", "AA12BC", readings)
    assert evidence.method == "fuzzy"
    assert evidence.score == 0.5


def test_ambiguidade_expoe_as_duas_datas_possiveis() -> None:
    text = "Data do sinistro: 03/02/2026\n"
    readings = read_field("date", "Data do sinistro", text)
    assert ambiguous_options(readings) == {"2026-02-03", "2026-03-02"}
    assert locate("date", "2026-02-03", readings).score == 0.0


def test_outros_valores_no_texto_sao_listados() -> None:
    text = "Data do sinistro: 18/02/2026\n"
    readings = read_field("date", "Data do sinistro", text)
    assert other_values("date", "2026-03-02", readings) == ["2026-02-18"]
    assert other_values("date", "2026-02-18", readings) == []


def test_so_as_linhas_rotuladas_sao_lidas() -> None:
    text = "Descrição: o valor estimado foi 1.520,00 €.\nValor reclamado: 1.250,50 €\n"
    readings = read_field("amount", "Valor reclamado", text)
    assert [r.raw for r in readings] == ["1.250,50 €"]
