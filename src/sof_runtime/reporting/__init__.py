from pathlib import Path
from typing import Any

from sof_runtime.contracts import load_json

from .assembly_v2 import assemble_report, artifact_reference
from .assembly_v2_1 import assemble_report as assemble_report_v2_1
from .migrator_v2_1 import migrate_report
from .validation_v2 import build_validation_receipt as build_validation_receipt_v2
from .validation_v2 import validate_receipt as validate_receipt_v2
from .validation_v2 import validate_report as validate_report_v2
from .validation_v2_1 import build_validation_receipt as build_validation_receipt_v2_1
from .validation_v2_1 import validate_receipt as validate_receipt_v2_1
from .validation_v2_1 import validate_report as validate_report_v2_1


def validate_report(path: str | Path, **kwargs: Any) -> dict[str, Any]:
    version = load_json(path).get("sofrs_version")
    if version == "2.1":
        return validate_report_v2_1(path, **kwargs)
    return validate_report_v2(path, **kwargs)


def validate_receipt(path: str | Path, **kwargs: Any) -> dict[str, Any]:
    version = load_json(path).get("receipt_version")
    if version == "2.1":
        return validate_receipt_v2_1(path, **kwargs)
    return validate_receipt_v2(path, **kwargs)


def build_validation_receipt(path: str | Path, **kwargs: Any) -> dict[str, Any]:
    version = load_json(path).get("sofrs_version")
    if version == "2.1":
        return build_validation_receipt_v2_1(path, **kwargs)
    return build_validation_receipt_v2(path, **kwargs)

__all__ = [
    "assemble_report",
    "assemble_report_v2_1",
    "artifact_reference",
    "build_validation_receipt",
    "validate_receipt",
    "validate_report",
    "validate_report_v2",
    "validate_report_v2_1",
    "migrate_report",
]
