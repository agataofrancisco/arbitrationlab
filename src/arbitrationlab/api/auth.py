"""Autenticacao demo por token Bearer. Cada token mapeia para um principal fixo (id + papel).

A identidade de quem actua vem SEMPRE do token. Cabecalhos declarados pelo cliente (como
`X-Actor`) nao sao lidos, por isso nao podem atribuir uma accao a outra pessoa.
"""

from __future__ import annotations

import hmac
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import Header, HTTPException, Request, status

Role = Literal["client", "reviewer"]


@dataclass(frozen=True)
class Principal:
    id: str
    role: Role


def resolve_principal(
    authorization: str | None,
    *,
    client_token: str,
    client_id: str,
    reviewer_token: str,
    reviewer_id: str,
) -> Principal | None:
    """Devolve o principal associado ao token Bearer, ou None se for invalido."""
    if not isinstance(authorization, str):
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    if hmac.compare_digest(token.encode(), reviewer_token.encode()):
        return Principal(id=reviewer_id, role="reviewer")
    if hmac.compare_digest(token.encode(), client_token.encode()):
        return Principal(id=client_id, role="client")
    return None


def require_principal(*allowed: Role) -> Callable[..., Principal]:
    """Dependencia FastAPI: 401 sem token valido, 403 se o papel nao for permitido."""

    def dependency(
        request: Request,
        authorization: Annotated[str | None, Header()] = None,
    ) -> Principal:
        settings = request.app.state.settings
        principal = resolve_principal(
            authorization,
            client_token=settings.client_token,
            client_id=settings.client_id,
            reviewer_token=settings.reviewer_token,
            reviewer_id=settings.reviewer_id,
        )
        if principal is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token ausente ou invalido")
        if principal.role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "papel sem permissao")
        return principal

    return dependency
