"""Fabrica da aplicacao FastAPI.

Erros internos nunca chegam ao cliente: a resposta tem uma mensagem generica e um
`request_id`; o detalhe fica apenas no log do servidor, associado a esse mesmo id.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from arbitrationlab import __version__
from arbitrationlab.api.routes import router
from arbitrationlab.config import Settings
from arbitrationlab.store.repository import ArbitrationStore

log = logging.getLogger("arbitrationlab.api")
GENERIC_ERROR = "erro interno do servidor"


def _request_id(request: Request) -> str:
    existing = getattr(request.state, "request_id", None)
    return existing if isinstance(existing, str) else uuid.uuid4().hex


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(title="ArbitrationLab", version=__version__)
    app.state.settings = settings
    app.state.store = ArbitrationStore(settings.database_url)

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    @app.exception_handler(Exception)
    async def unhandled_error(request: Request, exc: Exception) -> JSONResponse:
        request_id = _request_id(request)
        log.error(
            "pedido %s falhou em %s %s",
            request_id,
            request.method,
            request.url.path,
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return JSONResponse(
            status_code=500,
            content={"detail": GENERIC_ERROR, "request_id": request_id},
            headers={"X-Request-ID": request_id},
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    app.include_router(router)
    return app
