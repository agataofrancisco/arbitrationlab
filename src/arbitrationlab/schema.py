"""Schema dos campos de uma participacao de sinistro e validacao de schemas e candidatos.

Cada propriedade traz `x-type` (como normalizar) e `x-label` (rotulo no texto).
"""

from __future__ import annotations

import copy
from typing import Any

import jsonschema

CLAIM_FIELDS: tuple[str, ...] = (
    "policy_number",
    "incident_date",
    "license_plate",
    "claimed_amount",
    "currency",
    "third_party_involved",
    "injuries_reported",
)

_PROPERTIES: dict[str, dict[str, Any]] = {
    "policy_number": {"type": ["string", "null"], "x-type": "id", "x-label": "Apólice"},
    "incident_date": {
        "type": ["string", "null"],
        "x-type": "date",
        "x-label": "Data do sinistro",
    },
    "license_plate": {"type": ["string", "null"], "x-type": "plate", "x-label": "Matrícula"},
    "claimed_amount": {
        "type": ["string", "number", "null"],
        "x-type": "amount",
        "x-label": "Valor reclamado",
    },
    "currency": {"type": ["string", "null"], "x-type": "currency", "x-label": "Moeda"},
    "third_party_involved": {
        "type": ["boolean", "string", "null"],
        "x-type": "bool",
        "x-label": "Terceiro envolvido",
    },
    "injuries_reported": {
        "type": ["boolean", "string", "null"],
        "x-type": "bool",
        "x-label": "Feridos",
    },
}

CLAIM_OUTPUT_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": _PROPERTIES,
    "required": list(CLAIM_FIELDS),
    "additionalProperties": False,
}


def claim_output_schema() -> dict[str, Any]:
    """Copia independente do schema de sinistro, para os chamadores poderem alterar."""
    return copy.deepcopy(CLAIM_OUTPUT_SCHEMA)


def validate_output_schema(schema: Any) -> None:
    """Lanca ValueError se o schema nao for um JSON Schema valido (Draft 2020-12)."""
    if not isinstance(schema, dict):
        raise ValueError("o schema de saida tem de ser um objecto JSON")
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except jsonschema.SchemaError as exc:
        raise ValueError(f"schema de saida invalido: {exc.message}") from exc


def field_specs(schema: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Mapa campo -> {"x-type", "x-label"} a partir das propriedades do schema."""
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        return {}
    specs: dict[str, dict[str, str]] = {}
    for name, prop in properties.items():
        if not isinstance(prop, dict):
            continue
        x_type = prop.get("x-type", "text")
        x_label = prop.get("x-label", "")
        specs[name] = {
            "x-type": x_type if isinstance(x_type, str) else "text",
            "x-label": x_label if isinstance(x_label, str) else "",
        }
    return specs


def validate_candidate_output(schema: dict[str, Any], output: Any) -> list[str]:
    """Devolve a lista de erros (vazia se valido). Nunca lanca excepcao."""
    if not isinstance(output, dict):
        return ["a saida nao e um objecto JSON"]
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(output), key=lambda e: list(e.path))
    return [f"{'/'.join(str(p) for p in e.path) or '<raiz>'}: {e.message}" for e in errors]
