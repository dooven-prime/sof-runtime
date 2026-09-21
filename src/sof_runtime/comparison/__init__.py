from pathlib import Path
from typing import Any

from sof_runtime.contracts import load_json

from .validation_v2 import build_audit_validation_receipt as build_audit_validation_receipt_v2
from .validation_v2 import validate_audit as validate_audit_v2
from .validation_v2 import validate_audit_validation_receipt as validate_audit_validation_receipt_v2
from .validation_v2_1 import build_audit_validation_receipt as build_audit_validation_receipt_v2_1
from .validation_v2_1 import validate_audit as validate_audit_v2_1
from .validation_v2_1 import validate_audit_validation_receipt as validate_audit_validation_receipt_v2_1
from .producer_v2 import build_comparison as build_comparison_v2
from .producer_v2_1 import build_comparison
from .migrator_v2_1 import migrate_audit
from .evaluators import CoordinateEvaluatorRegistry


def validate_audit(path: str | Path, **kwargs: Any) -> dict[str, Any]:
    if load_json(path).get("sofaudit_version") == "2.1":
        return validate_audit_v2_1(path, **kwargs)
    return validate_audit_v2(path, **kwargs)


def validate_audit_validation_receipt(
    path: str | Path, **kwargs: Any
) -> dict[str, Any]:
    if load_json(path).get("receipt_version") == "2.1":
        return validate_audit_validation_receipt_v2_1(path, **kwargs)
    return validate_audit_validation_receipt_v2(path, **kwargs)


def build_audit_validation_receipt(
    path: str | Path, **kwargs: Any
) -> dict[str, Any]:
    if load_json(path).get("sofaudit_version") == "2.1":
        return build_audit_validation_receipt_v2_1(path, **kwargs)
    return build_audit_validation_receipt_v2(path, **kwargs)

__all__ = [
    "build_audit_validation_receipt",
    "validate_audit",
    "validate_audit_validation_receipt",
    "build_comparison",
    "build_comparison_v2",
    "validate_audit_v2",
    "validate_audit_v2_1",
    "CoordinateEvaluatorRegistry",
    "migrate_audit",
]
