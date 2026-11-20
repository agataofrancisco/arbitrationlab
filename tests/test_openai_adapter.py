"""Adaptador OpenAI-compativel testado com MockTransport (sem rede)."""

import asyncio
import json
from typing import Any

import httpx
import pytest

from arbitrationlab.generation.openai_compat import OpenAICompatibleProvider
from arbitrationlab.generation.providers import ProviderError


def _provider(transport: httpx.MockTransport) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        "modelo-teste",
        model="m",
        api_key="chave-falsa",
        cost_per_call_usd=0.001,
        transport=transport,
    )


def test_pedido_inclui_schema_e_documento_como_dados() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        content = json.dumps({"incident_date": "2026-02-03"})
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    provider = _provider(httpx.MockTransport(handler))
    result = asyncio.run(provider.extract("Data: 03/02/2026", {"type": "object"}))
    assert result == {"incident_date": "2026-02-03"}
    assert seen["auth"] == "Bearer chave-falsa"
    user_message = seen["body"]["messages"][1]["content"]
    assert "<documento>" in user_message
    assert "Data: 03/02/2026" in user_message


@pytest.mark.parametrize(
    ("status", "content"),
    [(500, "{}"), (200, "nao e json"), (200, "[1, 2]")],
)
def test_respostas_invalidas_viram_provider_error(status: int, content: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"choices": [{"message": {"content": content}}]})

    with pytest.raises(ProviderError):
        asyncio.run(_provider(httpx.MockTransport(handler)).extract("x", {}))


def test_falha_de_rede_nao_revela_a_chave() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sem rede")

    with pytest.raises(ProviderError) as info:
        asyncio.run(_provider(httpx.MockTransport(handler)).extract("x", {}))
    assert "chave-falsa" not in str(info.value)


def test_from_env_exige_chave() -> None:
    with pytest.raises(ValueError, match="ARBITRATIONLAB_OPENAI_API_KEY"):
        OpenAICompatibleProvider.from_env("x", model="m", cost_per_call_usd=0.1, env={})
