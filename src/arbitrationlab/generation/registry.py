"""Modelos mock predefinidos. Os precos sao simulados e ficam declarados nos relatorios."""

from __future__ import annotations

from arbitrationlab.generation.providers import ErrorProfile, MockProvider

PRICE_CHEAP_USD = 0.002
PRICE_STRONG_USD = 0.02
PRICE_VERIFIER_USD = 0.001
PRICE_JUDGE_USD = 0.01

CHEAP_A = "cheap-a"
CHEAP_B = "cheap-b"
STRONG_C = "strong-c"
VERIFIER = "verifier-v"
JUDGE = "judge-j"


def default_mock_models() -> dict[str, MockProvider]:
    """Tres candidatos com erros diferentes e um par que erra de forma correlacionada.

    - cheap-a e cheap-b leem a data trocando dia e mes em 15% dos documentos. Como o erro
      depende so do documento, os dois erram do mesmo modo (erro correlacionado).
    - Os modelos "cheap" leem o primeiro rotulo, por isso confundem rascunhos com valores finais.
    - strong-c le os rotulos sem qualificadores e tem omissoes independentes de 5%.
    """
    correlated = ErrorProfile(kind="date_swap", rate=0.15, correlated=True)
    return {
        CHEAP_A: MockProvider(
            CHEAP_A, parser="cheap", cost_per_call_usd=PRICE_CHEAP_USD, profile=correlated
        ),  # fmt: skip
        CHEAP_B: MockProvider(
            CHEAP_B, parser="cheap", cost_per_call_usd=PRICE_CHEAP_USD, profile=correlated
        ),  # fmt: skip
        STRONG_C: MockProvider(
            STRONG_C,
            parser="strong",
            cost_per_call_usd=PRICE_STRONG_USD,
            profile=ErrorProfile(kind="omit_field", rate=0.05, field="injuries_reported"),
        ),
        VERIFIER: MockProvider(VERIFIER, parser="cheap", cost_per_call_usd=PRICE_VERIFIER_USD),
        JUDGE: MockProvider(JUDGE, parser="strong", cost_per_call_usd=PRICE_JUDGE_USD),
    }
