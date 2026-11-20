"""Dataset sintetico: gerador determinista, validador e estatisticas."""

from pathlib import Path

from arbitrationlab.dataset.generator import DIFFICULTIES, generate_cases, to_jsonl, write_dataset
from arbitrationlab.dataset.validate import load_jsonl, stats, validate_cases

ROOT = Path(__file__).resolve().parents[1]
COMMITTED = ROOT / "datasets" / "claims" / "claims.jsonl"


def test_dataset_versionado_valida_e_tem_100_ou_mais_casos() -> None:
    cases = load_jsonl(COMMITTED)
    assert len(cases) >= 100
    assert validate_cases(cases) == []


def test_geracao_e_reprodutivel_e_bate_com_o_ficheiro_versionado() -> None:
    assert to_jsonl(generate_cases()) == COMMITTED.read_text(encoding="utf-8")


def test_cada_dificuldade_tem_casos_suficientes_e_split_40_60() -> None:
    summary = stats(load_jsonl(COMMITTED))
    assert set(summary["by_difficulty"]) == set(DIFFICULTIES)
    assert all(count >= 10 for count in summary["by_difficulty"].values())
    assert summary["by_split"] == {"calibration": 48, "evaluation": 72}


def test_casos_ambiguos_tem_dia_e_mes_menores_ou_iguais_a_12() -> None:
    cases = [c for c in load_jsonl(COMMITTED) if c["difficulty"] == "ambiguous_date"]
    assert cases
    for case in cases:
        day = int(case["gold"]["incident_date"][8:10])
        month = int(case["gold"]["incident_date"][5:7])
        assert day <= 12 and month <= 12


def test_validador_detecta_problemas() -> None:
    cases = load_jsonl(COMMITTED)
    broken = [dict(c) for c in cases[:5]]
    broken[0]["gold"] = {"policy_number": "X"}
    broken[1]["split"] = "treino"
    problems = validate_cases(broken)
    assert any("exactamente os campos" in p for p in problems)
    assert any("split invalido" in p for p in problems)
    assert any("sao precisos pelo menos 100" in p for p in problems)


def test_write_dataset_escreve_manifesto_com_hash(tmp_path: Path) -> None:
    manifest = write_dataset(tmp_path)
    assert manifest["n_cases"] == 120
    assert manifest["synthetic"] is True
    written = (tmp_path / "claims.jsonl").read_text(encoding="utf-8")
    assert written == COMMITTED.read_text(encoding="utf-8")
    assert len(manifest["sha256"]) == 64
