"""Avaliacao de um campo: acordo, evidencia, fiabilidade, confianca e decisao preliminar.

Regras, por ordem:
1. Sem nenhum candidato utilizavel -> human_review (no_usable_candidate).
2. Nenhum valor normalizavel: abstain se o campo nao existe no documento, senao human_review.
3. Valor sem evidencia no texto nunca e aceite:
   - ambiguo (ex.: 03/02/2026 com dia e mes <= 12) -> human_review (ambiguous_*)
   - o texto tem outro valor exacto -> human_review (evidence_conflict)
   - nenhuma leitura -> human_review (evidence_none)
4. Com evidencia: confianca calibrada >= accept -> accept; >= verify -> verify (pede verificacao
   barata); abaixo -> human_review (low_confidence).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Literal

from arbitrationlab.calibration import ConfidenceModel, ReliabilityTable
from arbitrationlab.decision.policy import Policy
from arbitrationlab.evidence import (
    Evidence,
    Reading,
    ambiguous_options,
    locate,
    other_values,
    read_field,
)
from arbitrationlab.normalize import normalize
from arbitrationlab.normalize.result import NormResult

Decision = Literal["accept", "verify", "human_review", "abstain"]


@dataclass(frozen=True)
class Vote:
    model: str
    candidate_status: str
    raw: Any
    result: NormResult | None


@dataclass(frozen=True)
class FieldAssessment:
    field: str
    decision: Decision
    reason: str
    suggested_value: Any
    confidence: float
    agreement: float
    evidence: Evidence
    reliability: float
    votes: tuple[Vote, ...]
    agreeing_models: tuple[str, ...] = ()
    flags: tuple[str, ...] = ()
    accepted_value: Any = None
    verification: dict[str, Any] | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def features(self) -> tuple[float, float, float]:
        return (self.agreement, self.evidence.score, self.reliability)


def _no_value_reason(votes: list[Vote]) -> tuple[Decision, str]:
    statuses = {v.result.status for v in votes if v.result is not None}
    if statuses <= {"missing"}:
        return "abstain", "missing_in_document"
    if "ambiguous" in statuses:
        return "human_review", "ambiguous_value"
    return "human_review", "unparseable_value"


def _assessment(
    name: str,
    decision: Decision,
    reason: str,
    votes: tuple[Vote, ...],
    **extra: Any,
) -> FieldAssessment:
    base: dict[str, Any] = {
        "suggested_value": None,
        "confidence": 0.0,
        "agreement": 0.0,
        "evidence": Evidence(score=0.0, method="none"),
        "reliability": 0.0,
    }
    base.update(extra)
    accepted = base.pop("accepted_value", None) if decision == "accept" else None
    return FieldAssessment(
        field=name,
        decision=decision,
        reason=reason,
        votes=votes,
        accepted_value=accepted,
        **base,
    )


def assess_field(
    name: str,
    field_type: str,
    label: str,
    text: str,
    raw_by_model: list[tuple[str, str, Any]],
    *,
    reliability: ReliabilityTable,
    calibrator: ConfidenceModel,
    policy: Policy,
    tainted_lines: frozenset[int] = frozenset(),
) -> FieldAssessment:
    """Decide um campo. `raw_by_model` tem (modelo, estado do candidato, valor bruto)."""
    votes = tuple(
        Vote(
            model=model,
            candidate_status=status,
            raw=raw,
            result=normalize(field_type, raw) if status == "ok" else None,
        )
        for model, status, raw in raw_by_model
    )
    usable = [v for v in votes if v.result is not None]
    flags: tuple[str, ...] = ("suspected_injection",) if tainted_lines else ()
    if not usable:
        return _assessment(name, "human_review", "no_usable_candidate", votes, flags=flags)

    values = [(v.model, v.result.value) for v in usable if v.result and v.result.ok]
    if not values:
        decision, reason = _no_value_reason(list(usable))
        return _assessment(name, decision, reason, votes, flags=flags)

    counts = Counter(value for _, value in values)
    top_value = counts.most_common(1)[0][0]
    agreeing = tuple(model for model, value in values if value == top_value)
    # Decisao nova: o denominador conta todos os candidatos pedidos, incluindo os que falharam.
    # Assim, um unico candidato sobrevivente nao atinge acordo total por si so.
    agreement = len(agreeing) / len(votes)
    readings: list[Reading] = read_field(field_type, label, text, tainted_lines=tainted_lines)
    evidence = locate(field_type, top_value, readings)
    reliability_score = sum(reliability.mean(m, name) for m in agreeing) / len(agreeing)
    confidence = calibrator.predict((agreement, evidence.score, reliability_score))
    common: dict[str, Any] = {
        "suggested_value": top_value,
        "confidence": confidence,
        "agreement": agreement,
        "evidence": evidence,
        "reliability": reliability_score,
        "agreeing_models": agreeing,
        "flags": flags,
    }

    if evidence.score == 0.0:
        if top_value in ambiguous_options(readings):
            return _assessment(name, "human_review", "ambiguous_value", votes, **common)
        conflicting = other_values(field_type, top_value, readings)
        if conflicting:
            return _assessment(name, "human_review", "evidence_conflict", votes, **common)
        return _assessment(name, "human_review", "evidence_none", votes, **common)

    if confidence >= policy.accept_threshold:
        return _assessment(
            name, "accept", "calibrated_accept", votes, accepted_value=top_value, **common
        )
    if confidence >= policy.verify_threshold:
        return _assessment(name, "verify", "needs_verification", votes, **common)
    return _assessment(name, "human_review", "low_confidence", votes, **common)
