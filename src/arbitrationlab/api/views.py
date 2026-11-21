"""Representacao JSON das arbitragens, dos campos e dos candidatos."""

from __future__ import annotations

from typing import Any

from arbitrationlab.store.models import ArbitrationRow, CandidateRow, FieldRow
from arbitrationlab.store.repository import REVIEWABLE


def _field_view(field: FieldRow) -> dict[str, Any]:
    reviewed = field.human_status is not None
    value = field.final_value if reviewed else field.accepted_value
    return {
        "decision": field.decision,
        "reason": field.reason,
        "value": value,
        "suggested_value": field.suggested_value,
        "confidence": round(field.confidence, 6),
        "agreement": round(field.agreement, 6),
        "reliability": round(field.reliability, 6),
        "evidence": field.evidence,
        "flags": list(field.flags),
        "verification": field.verification,
        "human_status": field.human_status,
        "pending_review": field.decision in REVIEWABLE and not reviewed,
    }


def arbitration_view(row: ArbitrationRow) -> dict[str, Any]:
    return {
        "arbitration_id": row.id,
        "task_id": row.task_id,
        "status": row.status,
        "error": row.error,
        "text": row.text,
        "max_spend": row.max_spend,
        "spent_usd": row.spent_usd,
        "suspected_injection": row.suspected_injection,
        "latency_ms": row.latency_ms,
        "judge": row.judge,
        "created_at": row.created_at.isoformat(),
        "fields": {f.field: _field_view(f) for f in row.fields},
        "pending_review": [
            f.field for f in row.fields if f.decision in REVIEWABLE and f.human_status is None
        ],
    }


def candidate_view(candidate: CandidateRow) -> dict[str, Any]:
    return {
        "model": candidate.model,
        "status": candidate.status,
        "output": candidate.output,
        "cost_usd": candidate.cost_usd,
        "latency_ms": round(candidate.latency_ms, 3),
        "reason": candidate.reason,
        "errors": list(candidate.errors),
    }
