"""Trabalho de fundo: corre a arbitragem com os modelos mock e grava o resultado."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from arbitrationlab.decision import Policy
from arbitrationlab.generation.registry import (
    CHEAP_A,
    CHEAP_B,
    JUDGE,
    STRONG_C,
    VERIFIER,
    default_mock_models,
)
from arbitrationlab.pipeline import arbitrate_sync
from arbitrationlab.store.repository import ArbitrationStore

log = logging.getLogger("arbitrationlab.jobs")

CANDIDATE_POOL: tuple[str, ...] = (CHEAP_A, CHEAP_B, STRONG_C)


def run_arbitration_job(
    store: ArbitrationStore,
    arbitration_id: str,
    *,
    text: str,
    output_schema: dict[str, Any],
    policy: Policy,
    max_spend: float,
) -> None:
    """Corre a arbitragem e grava o resultado. Falhas ficam registadas, nunca propagam."""
    models = default_mock_models()
    candidates = [models[name] for name in (policy.candidates or CANDIDATE_POOL)]
    run_policy = Policy(
        accept_threshold=policy.accept_threshold,
        verify_threshold=policy.verify_threshold,
        max_spend=max_spend,
        timeout_s=policy.timeout_s,
        candidates=policy.candidates,
        judge=policy.judge,
    )
    try:
        outcome = arbitrate_sync(
            text,
            output_schema,
            candidates,
            policy=run_policy,
            verifier=models[VERIFIER],
            judge=models[JUDGE],
        )
    except Exception:  # noqa: BLE001 - falha registada com referencia; detalhe so no log
        error_ref = uuid.uuid4().hex[:12]
        log.exception("arbitragem %s falhou (ref %s)", arbitration_id, error_ref)
        store.save_failure(arbitration_id, f"erro interno do servidor (ref {error_ref})")
        return
    store.save_outcome(arbitration_id, outcome)
