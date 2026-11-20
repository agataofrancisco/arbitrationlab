"""Fabrica da aplicacao FastAPI."""

from __future__ import annotations

from fastapi import FastAPI

from arbitrationlab import __version__
from arbitrationlab.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="ArbitrationLab", version=__version__)
    app.state.settings = settings or Settings.from_env()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    return app
