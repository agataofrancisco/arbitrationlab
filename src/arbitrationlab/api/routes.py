"""Rotas HTTP: pedido de arbitragem, consulta, candidatos, revisao humana, metricas e exportacao."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path, Request
from fastapi.responses import PlainTextResponse

from arbitrationlab.api.auth import Principal, require_principal
from arbitrationlab.api.jobs import CANDIDATE_POOL, run_arbitration_job
from arbitrationlab.api.schemas import ArbitrationIn, HumanReviewIn
from arbitrationlab.api.views import arbitration_view, candidate_view
from arbitrationlab.decision import Policy
from arbitrationlab.export import export_reviews_jsonl
from arbitrationlab.schema import claim_output_schema, validate_output_schema
from arbitrationlab.store.repository import ArbitrationStore, Decision, ReviewError, metrics

router = APIRouter()
ArbitrationId = Annotated[str, Path(pattern=r"^[0-9a-f]{32}$")]
ANY_ROLE = Depends(require_principal("client", "reviewer"))
REVIEWER = Depends(require_principal("reviewer"))


def _store(request: Request) -> ArbitrationStore:
    return request.app.state.store


def _load(store: ArbitrationStore, arbitration_id: str) -> Any:
    row = store.get(arbitration_id)
    if row is None:
        raise HTTPException(404, "arbitragem nao encontrada")
    return row


@router.get("/schemas/claim")
def get_claim_schema(principal: Annotated[Principal, ANY_ROLE]) -> dict[str, Any]:
    return claim_output_schema()


@router.post("/arbitrations", status_code=201)
def create_arbitration(
    body: ArbitrationIn,
    request: Request,
    background: BackgroundTasks,
    principal: Annotated[Principal, ANY_ROLE],
) -> dict[str, Any]:
    try:
        validate_output_schema(body.output_schema)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    names = body.policy.candidates
    if names is not None and any(n not in CANDIDATE_POOL for n in names):
        raise HTTPException(422, f"candidatos validos: {', '.join(CANDIDATE_POOL)}")
    settings = request.app.state.settings
    max_spend = settings.max_spend_default if body.max_spend is None else body.max_spend
    try:
        policy = Policy(
            accept_threshold=body.policy.accept_threshold,
            verify_threshold=body.policy.verify_threshold,
            max_spend=max_spend,
            timeout_s=settings.candidate_timeout_s,
            candidates=names,
            judge=body.policy.judge,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    store = _store(request)
    arbitration_id = store.new_id()
    store.create_pending(
        arbitration_id,
        task_id=body.task_id,
        text=body.text,
        output_schema=body.output_schema,
        policy=body.policy.model_dump(),
        max_spend=max_spend,
        created_by=principal.id,
    )
    background.add_task(
        run_arbitration_job,
        store,
        arbitration_id,
        text=body.text,
        output_schema=body.output_schema,
        policy=policy,
        max_spend=max_spend,
    )
    return {
        "arbitration_id": arbitration_id,
        "status": "pending",
        "links": {"self": f"/arbitrations/{arbitration_id}"},
    }


@router.get("/arbitrations/{arbitration_id}")
def get_arbitration(
    arbitration_id: ArbitrationId,
    request: Request,
    principal: Annotated[Principal, ANY_ROLE],
) -> dict[str, Any]:
    return arbitration_view(_load(_store(request), arbitration_id))


@router.get("/arbitrations/{arbitration_id}/candidates")
def get_candidates(
    arbitration_id: ArbitrationId,
    request: Request,
    principal: Annotated[Principal, ANY_ROLE],
) -> dict[str, Any]:
    row = _load(_store(request), arbitration_id)
    return {"arbitration_id": row.id, "candidates": [candidate_view(c) for c in row.candidates]}


@router.post("/arbitrations/{arbitration_id}/human-review")
def submit_review(
    arbitration_id: ArbitrationId,
    body: HumanReviewIn,
    request: Request,
    principal: Annotated[Principal, REVIEWER],
) -> dict[str, Any]:
    store = _store(request)
    decisions = [Decision(d.field, d.action, d.value) for d in body.decisions]
    try:
        store.review(arbitration_id, principal.id, decisions)
    except ReviewError as exc:
        raise HTTPException(exc.status, str(exc)) from exc
    return arbitration_view(_load(store, arbitration_id))


@router.get("/metrics")
def get_metrics(request: Request, principal: Annotated[Principal, ANY_ROLE]) -> dict[str, Any]:
    return metrics(_store(request))


@router.get("/reviews/export", response_class=PlainTextResponse)
def export_reviews(
    request: Request, principal: Annotated[Principal, REVIEWER]
) -> PlainTextResponse:
    return PlainTextResponse(
        export_reviews_jsonl(_store(request)), media_type="application/x-ndjson"
    )
