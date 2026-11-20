"""Autenticacao demo por token Bearer com papeis `client` e `reviewer`."""

from __future__ import annotations

import hmac
from collections.abc import Callable
from typing import Annotated, Literal

from fastapi import Header, HTTPException, Request, status

Role = Literal["client", "reviewer"]


def resolve_role(authorization: str | None, client_token: str, reviewer_token: str) -> Role | None:
    """Devolve o papel associado ao token Bearer, ou None se for invalido."""
    if not isinstance(authorization, str):
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    if hmac.compare_digest(token.encode(), reviewer_token.encode()):
        return "reviewer"
    if hmac.compare_digest(token.encode(), client_token.encode()):
        return "client"
    return None


def require_roles(*allowed: Role) -> Callable[..., Role]:
    """Dependencia FastAPI: 401 sem token valido, 403 se o papel nao for permitido."""

    def dependency(
        request: Request,
        authorization: Annotated[str | None, Header()] = None,
    ) -> Role:
        settings = request.app.state.settings
        role = resolve_role(authorization, settings.client_token, settings.reviewer_token)
        if role is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token ausente ou invalido")
        if role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "papel sem permissao")
        return role

    return dependency
