"""Verificacao barata de um campo: uma segunda leitura independente, que so conta se bater certo.

A verificacao chama um modelo barato focado no campo. A segunda leitura so e aceite se
normalizar para o mesmo valor e se tiver evidencia exacta no texto. Sem orcamento ou sem
verificador, o campo segue para revisao humana com o motivo registado.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from arbitrationlab.decision.assess import FieldAssessment
from arbitrationlab.evidence import locate, read_field
from arbitrationlab.normalize import normalize


def apply_verification(
    assessment: FieldAssessment,
    *,
    field_type: str,
    label: str,
    text: str,
    verified_raw: Any | None,
    skipped_reason: str | None = None,
    tainted_lines: frozenset[int] = frozenset(),
) -> FieldAssessment:
    """Fecha a decisao `verify`. `skipped_reason` indica porque nao houve verificacao."""
    if assessment.decision != "verify":
        return assessment
    if skipped_reason is not None or verified_raw is None:
        reason = skipped_reason or "verify_failed"
        return replace(
            assessment,
            decision="human_review",
            reason=reason,
            verification={"status": "not_run", "reason": reason},
        )
    result = normalize(field_type, verified_raw)
    readings = read_field(field_type, label, text, tainted_lines=tainted_lines)
    evidence = locate(field_type, assessment.suggested_value, readings)
    matches = result.ok and result.value == assessment.suggested_value
    supported = evidence.score > 0.0
    verification = {"status": "matched" if matches else "disagreed", "supported": supported}
    if matches and supported:
        return replace(
            assessment,
            decision="accept",
            reason="verified_by_second_reading",
            accepted_value=assessment.suggested_value,
            verification=verification,
        )
    return replace(
        assessment,
        decision="human_review",
        reason="verify_failed",
        verification=verification,
    )
