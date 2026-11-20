"""Geracao de candidatos: protocolo, mocks, adaptador OpenAI-compativel e runner paralelo."""

from arbitrationlab.generation.providers import (
    CandidateProvider,
    ErrorProfile,
    MockProvider,
    ProviderError,
)
from arbitrationlab.generation.runner import BudgetLedger, CandidateRecord, generate_candidates

__all__ = [
    "BudgetLedger",
    "CandidateProvider",
    "CandidateRecord",
    "ErrorProfile",
    "MockProvider",
    "ProviderError",
    "generate_candidates",
]
