"""Adaptador RegressionGuard (extra opcional). Todo o modulo e saltado sem o extra instalado."""

from pathlib import Path

import pytest

pytest.importorskip("regressionguard", reason="extra [regressionguard] nao instalado")

from regressionguard import (  # noqa: E402
    EvalContext,
    evaluator_names,
    get_evaluator,
)
from regressionguard.datasets.models import Case  # noqa: E402
from regressionguard.targets.base import TargetOutput  # noqa: E402

from arbitrationlab.integrations.regressionguard import (  # noqa: E402
    EVALUATOR_NAME,
    arbitration_output,
    build_smoke_dataset,
    claim_fields,
    ensure_registered,
    run_claim_suite,
)
from arbitrationlab.schema import CLAIM_FIELDS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SMOKE = ROOT / "experiments" / "regressionguard" / "claims-smoke.jsonl"
GOLD = {
    "policy_number": "HA-2026-004521",
    "incident_date": "2026-02-18",
    "license_plate": "AA12BC",
    "claimed_amount": 1250.5,
    "currency": "EUR",
    "third_party_involved": True,
    "injuries_reported": False,
}


def _case(expected: dict | None = None) -> Case:
    return Case(
        id="T-1",
        input="texto",
        expected=GOLD if expected is None else expected,
        category="clean",
        severity="normal",
        source="teste",
        evaluators=[EVALUATOR_NAME],
    )


def _output(accepted: dict, decisions: dict) -> TargetOutput:
    return TargetOutput(data={"accepted": accepted, "decisions": decisions})


def _ctx(output: TargetOutput, case: Case | None = None) -> EvalContext:
    return EvalContext(case=case or _case(), output=output, root=ROOT, judge=None)


def test_avaliador_esta_registado_no_registo_do_regressionguard() -> None:
    ensure_registered()
    ensure_registered()  # idempotente: nao deve lancar
    assert EVALUATOR_NAME in evaluator_names()
    assert get_evaluator(EVALUATOR_NAME).fn is claim_fields


def test_passa_quando_todos_os_campos_decididos_batem_com_o_gold() -> None:
    decisions = {name: "accept" for name in CLAIM_FIELDS}
    result = claim_fields(_ctx(_output(GOLD, decisions)))
    assert result.passed
    assert result.details["accepted_wrong"] == []


def test_falha_quando_um_valor_aceite_difere_do_gold() -> None:
    accepted = {**GOLD, "claimed_amount": 1520.0}
    decisions = {name: "accept" for name in CLAIM_FIELDS}
    result = claim_fields(_ctx(_output(accepted, decisions)))
    assert not result.passed
    assert result.reason == "accepted_wrong:claimed_amount"


def test_valor_errado_em_revisao_nao_conta_como_erro_aceite() -> None:
    accepted = {**GOLD, "claimed_amount": 1520.0}
    decisions = {name: "accept" for name in CLAIM_FIELDS}
    decisions["claimed_amount"] = "human_review"
    result = claim_fields(_ctx(_output(accepted, decisions)))
    assert result.passed
    assert result.details["undecided"] == 1


def test_campo_ausente_no_gold_aceite_com_valor_e_erro() -> None:
    expected = {**GOLD, "injuries_reported": None}
    accepted = {**expected, "injuries_reported": True}
    decisions = {name: "accept" for name in CLAIM_FIELDS}
    result = claim_fields(_ctx(_output(accepted, decisions), _case(expected)))
    assert result.reason == "accepted_wrong:injuries_reported"


def test_saida_sem_dados_da_arbitragem_falha_com_motivo_estavel() -> None:
    result = claim_fields(_ctx(TargetOutput(text="sem dados")))
    assert not result.passed
    assert result.reason == "no_arbitration_output"


def test_saida_real_da_arbitragem_tem_os_campos_esperados() -> None:
    output = arbitration_output("Data do sinistro: 18/02/2026\nValor reclamado: 1.250,50 €\n")
    assert set(output.data["accepted"]) == set(CLAIM_FIELDS)
    assert set(output.data["decisions"]) == set(CLAIM_FIELDS)
    assert output.cost_usd > 0


def test_suite_de_smoke_corre_pela_biblioteca_e_marca_o_ponto_cego() -> None:
    outcomes = run_claim_suite(SMOKE, root=ROOT)
    assert len(outcomes) == 8
    failing = [o for o in outcomes if not o.passed]
    # Unico caso falhado: rascunho aceite como valor final (ponto cego conhecido da evidencia).
    assert [o.case_id for o in failing] == ["CLM-0005"]
    assert failing[0].severity == "critical"
    assert failing[0].reason == "accepted_wrong:claimed_amount"


def test_suite_de_smoke_e_deterministica() -> None:
    first = run_claim_suite(SMOKE, root=ROOT)
    second = run_claim_suite(SMOKE, root=ROOT)
    assert first == second


def test_dataset_de_smoke_versionado_e_reproduzivel(tmp_path: Path) -> None:
    rebuilt = build_smoke_dataset(
        ROOT / "datasets" / "claims" / "claims.jsonl", tmp_path / "claims-smoke.jsonl"
    )
    assert rebuilt.read_text(encoding="utf-8") == SMOKE.read_text(encoding="utf-8")
