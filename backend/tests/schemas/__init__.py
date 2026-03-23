"""JSON Schema validation helpers for pipeline contracts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

_SCHEMAS_DIR = Path(__file__).parent


def validate_contract(data: Any, schema_name: str) -> None:
    """Validate *data* against a named JSON Schema file.

    Parameters
    ----------
    data:        The Python object to validate.
    schema_name: Schema filename WITHOUT extension (e.g. ``"contract_3_1"``).

    Raises
    ------
    jsonschema.ValidationError
        If validation fails.
    FileNotFoundError
        If the schema file does not exist.
    """
    schema_path = _SCHEMAS_DIR / f"{schema_name}.json"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=data, schema=schema)
