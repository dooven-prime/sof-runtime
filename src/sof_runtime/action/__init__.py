from pathlib import Path
from typing import Any

from sof_runtime.contracts import load_json

from .producer_v2 import build_interpretation as build_interpretation_v2
from .producer_v2_1 import build_interpretation
from .migrator_v2_1 import migrate_action
from .validation_v2 import build_action_validation_receipt as build_action_validation_receipt_v2
from .validation_v2 import validate_action as validate_action_v2
from .validation_v2 import validate_action_validation_receipt as validate_action_validation_receipt_v2
from .validation_v2_1 import build_action_validation_receipt as build_action_validation_receipt_v2_1
from .validation_v2_1 import validate_action as validate_action_v2_1
from .validation_v2_1 import validate_action_validation_receipt as validate_action_validation_receipt_v2_1


def validate_action(path: str | Path, **kwargs: Any) -> dict[str, Any]:
    if load_json(path).get("sofaction_version") == "2.1":
        return validate_action_v2_1(path, **kwargs)
    return validate_action_v2(path, **kwargs)


def validate_action_validation_receipt(
    path: str | Path, **kwargs: Any
) -> dict[str, Any]:
    if load_json(path).get("receipt_version") == "2.1":
        return validate_action_validation_receipt_v2_1(path, **kwargs)
    return validate_action_validation_receipt_v2(path, **kwargs)


def build_action_validation_receipt(
    path: str | Path, **kwargs: Any
) -> dict[str, Any]:
    if load_json(path).get("sofaction_version") == "2.1":
        return build_action_validation_receipt_v2_1(path, **kwargs)
    return build_action_validation_receipt_v2(path, **kwargs)

__all__ = [
    "build_action_validation_receipt",
    "validate_action",
    "validate_action_validation_receipt",
    "build_interpretation",
    "build_interpretation_v2",
    "validate_action_v2",
    "validate_action_v2_1",
    "migrate_action",
]
