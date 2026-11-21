"""Contratos HTTP (pydantic v2). Toda a entrada externa e validada aqui, na fronteira."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Name = Annotated[str, StringConstraints(min_length=1, max_length=64)]


class PolicyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["mock"] = "mock"
    candidates: list[Name] | None = Field(default=None, min_length=1, max_length=3)
    accept_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    verify_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    judge: bool = False


class ArbitrationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: Annotated[str, StringConstraints(min_length=1, max_length=100)]
    text: Annotated[str, StringConstraints(min_length=1, max_length=20_000)]
    output_schema: dict[str, Any]
    policy: PolicyIn = Field(default_factory=PolicyIn)
    max_spend: float | None = Field(default=None, ge=0.0, le=1.0)


class FieldDecisionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: Name
    action: Literal["confirm", "correct", "unreadable"]
    value: Any = None


class HumanReviewIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decisions: list[FieldDecisionIn] = Field(min_length=1, max_length=20)
