"""Repositorio: guarda arbitragens, aplica revisoes humanas com auditoria e calcula metricas."""

from __future__ import annotations

import uuid
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from arbitrationlab.normalize import normalize
from arbitrationlab.pipeline import Outcome
from arbitrationlab.store.models import (
    ArbitrationRow,
    Base,
    CandidateRow,
    FieldRow,
    ReviewRow,
)

REVIEWABLE = frozenset({"human_review", "abstain"})
ACTIONS = frozenset({"confirm", "correct", "unreadable"})


class ReviewError(Exception):
    """Revisao recusada. `status` e o codigo HTTP sugerido."""

    def __init__(self, message: str, status: int) -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class Decision:
    field: str
    action: str
    value: Any = None


def _engine(database_url: str) -> Engine:
    if database_url.startswith("sqlite"):
        if ":memory:" in database_url or database_url == "sqlite://":
            return create_engine(
                database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        path = database_url.removeprefix("sqlite:///")
        if path:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        return create_engine(database_url, connect_args={"check_same_thread": False})
    return create_engine(database_url)


class ArbitrationStore:
    def __init__(self, database_url: str) -> None:
        self.engine = _engine(database_url)
        Base.metadata.create_all(self.engine)
        self._sessions = sessionmaker(bind=self.engine, expire_on_commit=False)

    def new_id(self) -> str:
        return uuid.uuid4().hex

    def session(self) -> Session:
        """Sessao de leitura para consultas (metricas, exportacao)."""
        return self._sessions()

    def create_pending(
        self,
        arbitration_id: str,
        *,
        task_id: str,
        text: str,
        output_schema: dict[str, Any],
        policy: dict[str, Any],
        max_spend: float,
        created_by: str,
    ) -> None:
        with self._sessions.begin() as session:
            session.add(
                ArbitrationRow(
                    id=arbitration_id,
                    task_id=task_id,
                    status="pending",
                    text=text,
                    output_schema=output_schema,
                    policy=policy,
                    max_spend=max_spend,
                    created_by=created_by,
                )
            )

    def save_outcome(self, arbitration_id: str, outcome: Outcome) -> None:
        with self._sessions.begin() as session:
            row = session.get(ArbitrationRow, arbitration_id)
            if row is None:
                raise KeyError(arbitration_id)
            row.status = "completed"
            row.spent_usd = outcome.spent_usd
            row.suspected_injection = outcome.suspected_injection
            row.latency_ms = outcome.latency_ms
            row.judge = outcome.judge_suggestion
            for position, record in enumerate(outcome.candidates):
                row.candidates.append(
                    CandidateRow(
                        position=position,
                        model=record.model,
                        status=record.status,
                        output=record.output,
                        cost_usd=record.cost_usd,
                        latency_ms=record.latency_ms,
                        reason=record.reason,
                        errors=list(record.errors),
                    )
                )
            for position, (name, verdict) in enumerate(outcome.verdicts.items()):
                row.fields.append(
                    FieldRow(
                        position=position,
                        field=name,
                        decision=verdict.decision,
                        reason=verdict.reason,
                        suggested_value=verdict.suggested_value,
                        accepted_value=verdict.accepted_value,
                        confidence=verdict.confidence,
                        agreement=verdict.agreement,
                        reliability=verdict.reliability,
                        evidence=_evidence_dict(verdict.evidence),
                        flags=list(verdict.flags),
                        verification=verdict.verification,
                        final_value=verdict.accepted_value,
                    )
                )

    def save_failure(self, arbitration_id: str, message: str) -> None:
        with self._sessions.begin() as session:
            row = session.get(ArbitrationRow, arbitration_id)
            if row is not None:
                row.status = "failed"
                row.error = message[:500]

    def get(self, arbitration_id: str) -> ArbitrationRow | None:
        with self._sessions() as session:
            return session.get(ArbitrationRow, arbitration_id)

    def review(self, arbitration_id: str, actor: str, decisions: Iterable[Decision]) -> None:
        """Aplica decisoes humanas a campos pendentes e regista cada alteracao na auditoria."""
        items = list(decisions)
        with self._sessions.begin() as session:
            row = session.get(ArbitrationRow, arbitration_id)
            if row is None:
                raise ReviewError("arbitragem nao encontrada", 404)
            if row.status != "completed":
                raise ReviewError("a arbitragem nao esta concluida", 409)
            by_field = {f.field: f for f in row.fields}
            seen: set[str] = set()
            for item in items:
                if item.field in seen:
                    raise ReviewError(f"campo repetido: {item.field}", 422)
                seen.add(item.field)
                _apply_one(session, row, by_field, item, actor)


def _apply_one(
    session: Session,
    row: ArbitrationRow,
    by_field: dict[str, FieldRow],
    item: Decision,
    actor: str,
) -> None:
    field_row = by_field.get(item.field)
    if field_row is None:
        raise ReviewError(f"campo desconhecido: {item.field}", 422)
    if item.action not in ACTIONS:
        raise ReviewError(f"accao invalida: {item.action}", 422)
    if field_row.decision not in REVIEWABLE or field_row.human_status is not None:
        raise ReviewError(f"o campo {item.field} nao esta pendente de revisao", 409)
    old_value = field_row.final_value
    if item.action == "unreadable":
        new_value = None
        status = "unreadable"
    else:
        if item.action == "confirm":
            candidate = field_row.suggested_value
            if candidate is None:
                raise ReviewError(f"{item.field} nao tem valor sugerido para confirmar", 422)
        else:
            if item.value is None:
                raise ReviewError(f"{item.field} precisa de um valor para corrigir", 422)
            result = normalize(_field_type(row, item.field), item.value)
            if not result.ok:
                raise ReviewError(f"valor invalido para {item.field}: {result.status}", 422)
            candidate = result.value
        new_value = candidate
        status = "accepted_by_human"
    field_row.human_status = status
    field_row.final_value = new_value
    session.add(
        ReviewRow(
            arbitration_id=row.id,
            field=item.field,
            action=item.action,
            actor=actor,
            old_value=old_value,
            new_value=new_value,
            text=row.text,
        )
    )


def _field_type(row: ArbitrationRow, field: str) -> str:
    properties = row.output_schema.get("properties", {})
    spec = properties.get(field, {}) if isinstance(properties, dict) else {}
    x_type = spec.get("x-type", "text") if isinstance(spec, dict) else "text"
    return x_type if isinstance(x_type, str) else "text"


def _evidence_dict(evidence: Any) -> dict[str, Any]:
    return {
        "score": evidence.score,
        "method": evidence.method,
        "start": evidence.start,
        "end": evidence.end,
        "text": evidence.text,
    }


def metrics(store: ArbitrationStore) -> dict[str, Any]:
    """Contagens e custos medidos a partir da base de dados (nunca estimados)."""
    with store.session() as session:
        by_status = Counter(s for (s,) in session.execute(select(ArbitrationRow.status)).all())
        decisions = Counter(d for (d,) in session.execute(select(FieldRow.decision)).all())
        reviews = session.scalar(select(func.count()).select_from(ReviewRow)) or 0
        spent = session.scalar(select(func.coalesce(func.sum(ArbitrationRow.spent_usd), 0.0)))
        latency = session.scalar(select(func.coalesce(func.avg(ArbitrationRow.latency_ms), 0.0)))
    return {
        "arbitrations": dict(sorted(by_status.items())),
        "field_decisions": dict(sorted(decisions.items())),
        "reviews": int(reviews),
        "total_spent_usd": round(float(spent or 0.0), 6),
        "mean_latency_ms": round(float(latency or 0.0), 3),
        "provider": "mock",
    }


def human_reviews(store: ArbitrationStore) -> list[dict[str, Any]]:
    """Revisoes humanas (uma linha por campo) com o texto e o valor final, para exportacao."""
    with store.session() as session:
        rows = session.execute(select(ReviewRow).order_by(ReviewRow.id)).scalars().all()
        return [
            {
                "arbitration_id": r.arbitration_id,
                "field": r.field,
                "action": r.action,
                "actor": r.actor,
                "old_value": r.old_value,
                "new_value": r.new_value,
                "text": r.text,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
