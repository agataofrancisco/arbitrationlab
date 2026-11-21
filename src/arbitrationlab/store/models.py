"""Modelos SQLAlchemy: arbitragens, candidatos, decisoes por campo e auditoria de revisoes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class ArbitrationRow(Base):
    __tablename__ = "arbitrations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), index=True)
    text: Mapped[str] = mapped_column(Text)
    output_schema: Mapped[dict[str, Any]] = mapped_column(JSON)
    policy: Mapped[dict[str, Any]] = mapped_column(JSON)
    max_spend: Mapped[float] = mapped_column(Float)
    spent_usd: Mapped[float] = mapped_column(Float, default=0.0)
    suspected_injection: Mapped[bool] = mapped_column(Boolean, default=False)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    judge: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    candidates: Mapped[list[CandidateRow]] = relationship(
        cascade="all, delete-orphan", order_by="CandidateRow.position", lazy="selectin"
    )
    fields: Mapped[list[FieldRow]] = relationship(
        cascade="all, delete-orphan", order_by="FieldRow.position", lazy="selectin"
    )


class CandidateRow(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    arbitration_id: Mapped[str] = mapped_column(ForeignKey("arbitrations.id"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    model: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20))
    output: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    cost_usd: Mapped[float] = mapped_column(Float)
    latency_ms: Mapped[float] = mapped_column(Float)
    reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    errors: Mapped[list[str]] = mapped_column(JSON, default=list)


class FieldRow(Base):
    __tablename__ = "fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    arbitration_id: Mapped[str] = mapped_column(ForeignKey("arbitrations.id"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    field: Mapped[str] = mapped_column(String(64))
    decision: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(String(200))
    suggested_value: Mapped[Any] = mapped_column(JSON, nullable=True)
    accepted_value: Mapped[Any] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float] = mapped_column(Float)
    agreement: Mapped[float] = mapped_column(Float)
    reliability: Mapped[float] = mapped_column(Float)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON)
    flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    verification: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    human_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    final_value: Mapped[Any] = mapped_column(JSON, nullable=True)


class ReviewRow(Base):
    """Auditoria: quem, quando, valor anterior e novo de cada decisao humana."""

    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    arbitration_id: Mapped[str] = mapped_column(ForeignKey("arbitrations.id"), index=True)
    field: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(20))
    actor: Mapped[str] = mapped_column(String(64))
    old_value: Mapped[Any] = mapped_column(JSON, nullable=True)
    new_value: Mapped[Any] = mapped_column(JSON, nullable=True)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
