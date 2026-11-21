"""Fabrica da aplicacao FastAPI."""

from __future__ import annotations

from fastapi import FastAPI

from arbitrationlab import __version__
from arbitrationlab.api.routes import router
from arbitrationlab.config import Settings
from arbitrationlab.store.repository import ArbitrationStore


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(title="ArbitrationLab", version=__version__)
    app.state.settings = settings
    app.state.store = ArbitrationStore(settings.database_url)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    app.include_router(router)
    return app
