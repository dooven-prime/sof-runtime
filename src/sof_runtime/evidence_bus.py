from __future__ import annotations

from pathlib import Path
from typing import Any

from sof_runtime.artifacts import canonical_json_bytes, sha256_bytes, sha256_file
from sof_runtime.contracts import load_json, validate_contract
from sof_runtime.paths import PROJECT_ROOT, RUNTIME_CONTRACT_ROOT
from sof_runtime.run_identity import verify_semantic_run_id


def relative_path(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT).as_posix()


def runtime_ref(
    artifact: dict[str, Any],
    *,
    schema_id: str | None,
    producer: str,
    input_refs: list[str],
) -> dict[str, Any]:
    return {
        "artifact_id": artifact["id"],
        "media_type": artifact["media_type"],
        "uri": artifact["uri"],
        "sha256": artifact["digest"]["value"],
        "schema_id": schema_id,
        "producer": producer,
        "input_refs": input_refs,
    }


def output_item(
    *,
    kind: str,
    convenience_path: Path,
    artifact: dict[str, Any],
    schema_id: str | None,
    producer: str,
    input_refs: list[str],
) -> dict[str, Any]:
    return {
        "kind": kind,
        "path": relative_path(convenience_path),
        "artifact_ref": runtime_ref(
            artifact,
            schema_id=schema_id,
            producer=producer,
            input_refs=input_refs,
        ),
    }


def validator_independence(
    request: dict[str, Any],
    *,
    implementation_relation: str,
) -> dict[str, Any]:
    environment = request["runtime_environment"]
    language = environment["implementation_language"]
    return {
        "implementation_relation": implementation_relation,
        "language_relation": (
            "same_language"
            if language == "python"
            else "unknown_language"
            if language == "unknown"
            else "different_language"
        ),
        "runtime_relation": (
            "separate_process"
            if environment["execution_mode"] == "external_executable"
            else "same_process"
        ),
        "input_source": "canonical_source_artifacts",
        "producer_cache_used": False,
    }


def build_artifact_closure(outputs: list[dict[str, Any]]) -> dict[str, Any]:
    artifacts = sorted(
        (
            {
                "artifact_id": item["artifact_ref"]["artifact_id"],
                "kind": item["kind"],
                "media_type": item["artifact_ref"]["media_type"],
                "uri": item["artifact_ref"]["uri"],
                "sha256": item["artifact_ref"]["sha256"],
                "schema_id": item["artifact_ref"]["schema_id"],
                "producer": item["artifact_ref"]["producer"],
                "input_refs": item["artifact_ref"]["input_refs"],
            }
            for item in outputs
        ),
        key=lambda item: item["artifact_id"],
    )
    artifact_ids = [item["artifact_id"] for item in artifacts]
    if len(artifact_ids) != len(set(artifact_ids)):
        raise ValueError("artifact closure contains duplicate artifact IDs")
    certificate_digests = [
        item["sha256"]
        for item in artifacts
        if item["kind"] == "validation_certificate"
    ]
    if len(certificate_digests) > 1:
        raise ValueError("artifact closure contains multiple validation certificates")
    return {
        "closure_profile": "sof-artifact-closure-v1",
        "artifact_manifest_digest": sha256_bytes(canonical_json_bytes(artifacts)),
        "artifact_count": len(artifacts),
        "ordered_artifact_ids": artifact_ids,
        "artifacts": artifacts,
        "validator_certificate_digest": (
            certificate_digests[0] if certificate_digests else None
        ),
    }


def failure_response(
    request: dict[str, Any],
    *,
    validator_id: str,
    validator_version: str,
    status: str,
    stage: str,
    error: Exception,
    outputs: list[dict[str, Any]],
    stderr: bytes = b"",
    retryable: bool = False,
    validator_ran: bool = False,
) -> dict[str, Any]:
    response = {
        "schema_id": "sof.run-response.v1",
        "semantic_run_id": request["semantic_run_id"],
        "execution_id": request["execution_id"],
        "request_digest": sha256_bytes(canonical_json_bytes(request)),
        "plugin": request["plugin"],
        "carrier_kind": request["carrier_kind"],
        "status": status,
        "artifact_directory": request["artifact_directory"],
        "outputs": outputs,
        "artifact_closure": build_artifact_closure(outputs),
        "validator": {
            "validator_id": validator_id,
            "validator_version": validator_version,
            "ran": validator_ran,
        },
        "failure": {
            "stage": stage,
            "error_type": type(error).__name__,
            "message": str(error) or type(error).__name__,
            "stderr_sha256": sha256_bytes(stderr) if stderr else None,
            "retryable": retryable,
            "generated_artifact_ids": [
                item["artifact_ref"]["artifact_id"] for item in outputs
            ],
            "usable_finding_count": 0,
            "validator_ran": validator_ran,
        },
        "diagnostics": [f"{stage}: {type(error).__name__}"],
    }
    validate_contract(
        response,
        RUNTIME_CONTRACT_ROOT / "run-response.schema.json",
        label="RunResponse",
    )
    return response


def verify_response_artifacts(
    response_path: str | Path,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, Any]]:
    response = load_json(response_path)
    validate_contract(
        response,
        RUNTIME_CONTRACT_ROOT / "run-response.schema.json",
        label="RunResponse",
    )
    output_kinds = [item["kind"] for item in response["outputs"]]
    if len(output_kinds) != len(set(output_kinds)):
        raise ValueError("RunResponse contains duplicate output kinds")
    outputs = {item["kind"]: item for item in response["outputs"]}
    expected_closure = build_artifact_closure(response["outputs"])
    if response["artifact_closure"] != expected_closure:
        raise ValueError("RunResponse artifact closure mismatch")
    if "run_request" not in outputs:
        raise ValueError("RunResponse is missing its RunRequest artifact")

    artifact_root = (PROJECT_ROOT / response["artifact_directory"]).resolve()
    try:
        artifact_root.relative_to(PROJECT_ROOT)
    except ValueError as error:
        raise ValueError("artifact directory escapes the repository") from error
    for item in outputs.values():
        ref = item["artifact_ref"]
        artifact_path = (PROJECT_ROOT / ref["uri"]).resolve()
        try:
            artifact_path.relative_to(artifact_root)
        except ValueError as error:
            raise ValueError(
                f"artifact URI escapes artifact directory: {ref['artifact_id']}"
            ) from error
        if not artifact_path.is_file() or sha256_file(artifact_path) != ref["sha256"]:
            raise ValueError(f"artifact verification failed: {ref['artifact_id']}")
        convenience_path = (PROJECT_ROOT / item["path"]).resolve()
        try:
            convenience_path.relative_to(PROJECT_ROOT)
        except ValueError as error:
            raise ValueError(f"output path escapes repository: {item['kind']}") from error
        if not convenience_path.is_file():
            raise ValueError(f"output path is missing: {item['kind']}")

    request = load_json(PROJECT_ROOT / outputs["run_request"]["artifact_ref"]["uri"])
    validate_contract(
        request,
        RUNTIME_CONTRACT_ROOT / "run-request.schema.json",
        label="RunRequest",
    )
    if not verify_semantic_run_id(request):
        raise ValueError("RunRequest semantic identity mismatch")
    if response["request_digest"] != sha256_bytes(canonical_json_bytes(request)):
        raise ValueError("RunResponse request digest mismatch")
    for field in ("semantic_run_id", "execution_id", "plugin", "carrier_kind"):
        if response[field] != request[field]:
            raise ValueError(f"RunResponse does not bind RunRequest field {field}")
    return response, outputs, request


def verify_promotion_artifact_closure(
    promotion: dict[str, Any],
    response: dict[str, Any],
) -> None:
    closure_digest = response["artifact_closure"]["artifact_manifest_digest"]
    if promotion["run_response_artifact_closure_digest"] != closure_digest:
        raise ValueError("Promotion Package artifact closure digest mismatch")

    refs = promotion["artifact_refs"]
    ref_ids = [item["artifact_id"] for item in refs]
    if len(ref_ids) != len(set(ref_ids)):
        raise ValueError("Promotion Package contains duplicate artifact IDs")
    package_refs = {item["artifact_id"]: item for item in refs}
    expected_refs = {
        item["artifact_ref"]["artifact_id"]: item["artifact_ref"]
        for item in response["outputs"]
    }
    expected_ids = set(expected_refs) | {"artifact.run-response"}
    if set(package_refs) != expected_ids:
        raise ValueError("Promotion Package artifact set differs from RunResponse closure")
    for artifact_id, expected in expected_refs.items():
        if package_refs[artifact_id] != expected:
            raise ValueError(
                f"Promotion Package artifact differs from RunResponse closure: {artifact_id}"
            )

    response_digest = sha256_bytes(canonical_json_bytes(response))
    response_ref = package_refs["artifact.run-response"]
    if response_ref["sha256"] != response_digest:
        raise ValueError("Promotion Package does not bind the frozen RunResponse")
    response_artifact = (PROJECT_ROOT / response_ref["uri"]).resolve()
    if not response_artifact.is_file() or sha256_file(response_artifact) != response_digest:
        raise ValueError("frozen RunResponse artifact verification failed")
