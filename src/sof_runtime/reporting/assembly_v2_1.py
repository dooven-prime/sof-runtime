"""Native SOFRS v2.1 assembly over the frozen v2.0 faithful assembler."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from sof_runtime.contracts import validate_contract
from sof_runtime.non_intervention import SOFRS_OBJECT_TRANSITION_BOUNDARY
from sof_runtime.paths import PROJECT_ROOT, REPORTING_V2_1_CONTRACT_ROOT

from .assembly_v2 import assemble_report as assemble_report_v2
from .assembly_v2 import artifact_reference, resolve_artifact_reference


REPORT_SCHEMA = REPORTING_V2_1_CONTRACT_ROOT / "sofrs.schema.json"


def assemble_report(
    manifest_path: str | Path,
    ir_path: str | Path,
    compiler_profile_path: str | Path,
    compiler_output_path: str | Path,
    assembly_profile_path: str | Path,
    *,
    assembly_implementation: dict[str, Any],
    generation_implementation: dict[str, Any],
    generation_inputs: list[dict[str, Any]],
    presentation: dict[str, Any],
    repository_root: str | Path = PROJECT_ROOT,
    verify_artifacts: bool = True,
) -> dict[str, Any]:
    """Assemble a native v2.1 report and bind its complete generation inputs."""

    if not generation_inputs:
        raise ValueError("SOFRS v2.1 native generation requires at least one input")
    report = assemble_report_v2(
        manifest_path,
        ir_path,
        compiler_profile_path,
        compiler_output_path,
        assembly_profile_path,
        assembly_implementation=assembly_implementation,
        presentation=presentation,
        repository_root=repository_root,
        verify_artifacts=verify_artifacts,
    )
    report["sofrs_version"] = "2.1"
    report["revision_provenance"] = {
        "kind": "native_v2_1_generation",
        "generation_implementation": deepcopy(generation_implementation),
        "generation_inputs": deepcopy(generation_inputs),
    }
    report["object_transition_boundary"] = deepcopy(
        SOFRS_OBJECT_TRANSITION_BOUNDARY
    )
    validate_contract(report, REPORT_SCHEMA, label="SOFRS v2.1 report")
    return report


__all__ = ["assemble_report", "artifact_reference", "resolve_artifact_reference"]
