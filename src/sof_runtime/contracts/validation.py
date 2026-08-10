from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


class ContractError(ValueError):
    """Raised when a payload violates a versioned JSON contract."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_nonstandard_number(value: str) -> None:
    raise ContractError(f"non-standard JSON numeric literal: {value}")


def _parse_integer(value: str) -> int:
    if value == "-0":
        raise ContractError("negative-zero JSON integer is forbidden")
    return int(value)


def loads_json(text: str) -> Any:
    return json.loads(
        text,
        object_pairs_hook=_unique_object,
        parse_constant=_reject_nonstandard_number,
        parse_int=_parse_integer,
    )


def load_json(path: str | Path) -> Any:
    return loads_json(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: Any) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def validation_errors(payload: Any, schema: dict[str, Any]) -> list[str]:
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    return [
        f"{'.'.join(str(part) for part in error.path) or '<root>'}: {error.message}"
        for error in sorted(
            validator.iter_errors(payload),
            key=lambda item: [str(part) for part in item.path],
        )
    ]


def validate_contract(
    payload: Any,
    schema_path: str | Path,
    *,
    label: str = "payload",
) -> None:
    errors = validation_errors(payload, load_json(schema_path))
    if errors:
        raise ContractError(f"{label} contract failed: " + "; ".join(errors))
