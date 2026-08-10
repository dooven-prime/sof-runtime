from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sof_runtime.adapters.automata import build_manifest, normalize_source
from sof_runtime.artifacts import (
    ArtifactStore,
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)
from sof_runtime.carriers.rank_collapse import (
    PLUGIN_ID,
    PLUGIN_VERSION,
    SUPPORTED_POLICY,
    RankCollapsePlugin,
    UnsupportedRankCollapsePolicy,
)
from sof_runtime.contracts import ContractError, load_json, validate_contract
from sof_runtime.contracts.validation import write_json
from sof_runtime.evidence_bus import (
    build_artifact_closure,
    failure_response,
    output_item,
    relative_path,
    runtime_ref,
    validator_independence,
    verify_promotion_artifact_closure,
    verify_response_artifacts,
)
from sof_runtime.paths import (
    COMPILER_CONTRACT_ROOT,
    PROJECT_ROOT,
    RANK_COLLAPSE_CONTRACT_ROOT,
    RUNTIME_CONTRACT_ROOT,
)
from sof_runtime.plugins import CarrierPlugin, PluginExecutionError
from sof_runtime.run_identity import (
    CANONICAL_JSON_PROFILE,
    compute_semantic_run_id,
    new_execution_id,
    runtime_environment_for,
    semantic_environment_for,
    verify_semantic_run_id,
)
from sof_runtime.validation.rank_collapse import (
    VALIDATOR_ID,
    VALIDATOR_VERSION,
    validate_rank_collapse,
)


CONTRACT_VERSIONS = {
    "canonical_json": CANONICAL_JSON_PROFILE,
    "runtime": "1.0",
    "source": "rime.automata.source.v1",
    "extension": "rime.rank-collapse.bundle.v1",
}


def _validate_rank_bundle(bundle: dict[str, Any]) -> None:
    validate_contract(
        bundle,
        RANK_COLLAPSE_CONTRACT_ROOT / "bundle.schema.json",
        label="rank-collapse bundle",
    )
    validate_contract(
        bundle["object"],
        RANK_COLLAPSE_CONTRACT_ROOT / "object.schema.json",
        label="rank-collapse object",
    )
    for item in bundle["findings"]:
        validate_contract(
            item["envelope"],
            RUNTIME_CONTRACT_ROOT / "finding-envelope.schema.json",
            label="finding envelope",
        )
        validate_contract(
            item["payload"],
            RANK_COLLAPSE_CONTRACT_ROOT / "finding.schema.json",
            label="rank-collapse finding",
        )


def build_rank_collapse_request(
    source: dict[str, Any],
    run_directory: str | Path,
    *,
    plugin: CarrierPlugin | None = None,
    policies: dict[str, Any] | None = None,
    execution_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    selected_plugin = plugin or RankCollapsePlugin()
    selected_policies = policies if policies is not None else SUPPORTED_POLICY
    run_dir = Path(run_directory).resolve()
    try:
        run_dir.relative_to(PROJECT_ROOT)
    except ValueError as error:
        raise ValueError("run directory must remain inside the sof-runtime repository") from error
    timestamp = created_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    plugin_identity = {
        "plugin_id": selected_plugin.plugin_id,
        "plugin_version": selected_plugin.plugin_version,
    }
    runtime_environment = runtime_environment_for(selected_plugin)
    semantic_environment = semantic_environment_for(selected_plugin)
    semantic_run_id = compute_semantic_run_id(
        source=source,
        plugin=plugin_identity,
        carrier_kind="rank_collapse",
        contract_versions=CONTRACT_VERSIONS,
        policies=selected_policies,
        semantic_environment=semantic_environment,
    )
    request = {
        "schema_id": "sof.run-request.v1",
        "semantic_run_id": semantic_run_id,
        "execution_id": execution_id
        or new_execution_id(
            semantic_run_id=semantic_run_id,
            runtime_environment=runtime_environment,
            started_at=timestamp,
        ),
        "created_at": timestamp,
        "plugin": plugin_identity,
        "carrier_kind": "rank_collapse",
        "contract_versions": CONTRACT_VERSIONS,
        "semantic_environment": semantic_environment,
        "runtime_environment": runtime_environment,
        "source": source,
        "policies": selected_policies,
        "artifact_directory": relative_path(run_dir / "artifacts" / "sha256"),
    }
    validate_contract(
        request,
        RUNTIME_CONTRACT_ROOT / "run-request.schema.json",
        label="RunRequest",
    )
    if not verify_semantic_run_id(request):
        raise ContractError("RunRequest semantic identity is invalid")
    return request


def _failure_response(
    request: dict[str, Any],
    *,
    status: str,
    stage: str,
    error: Exception,
    outputs: list[dict[str, Any]],
    stderr: bytes = b"",
    retryable: bool = False,
    validator_ran: bool = False,
) -> dict[str, Any]:
    return failure_response(
        request,
        validator_id=VALIDATOR_ID,
        validator_version=VALIDATOR_VERSION,
        status=status,
        stage=stage,
        error=error,
        outputs=outputs,
        stderr=stderr,
        retryable=retryable,
        validator_ran=validator_ran,
    )


def _promotion_package(
    request: dict[str, Any],
    artifact_refs: list[dict[str, Any]],
    artifact_closure_digest: str,
) -> dict[str, Any]:
    package = {
        "schema_id": "sof.promotion-package.v1",
        "package_id": "promotion:rank-collapse:" + request["semantic_run_id"].split(":")[-1],
        "promotion_state": "CANDIDATE",
        "semantic_run_id": request["semantic_run_id"],
        "execution_ids": [request["execution_id"]],
        "run_response_artifact_closure_digest": artifact_closure_digest,
        "candidate": {
            "extension_id": "rank-collapse",
            "extension_version": "1.0",
            "proposed_carrier_kind": "rank_collapse",
            "semantics": "First-hit depth for the image rank of a common labelled word acting on the full state set.",
        },
        "artifact_refs": artifact_refs,
        "validator": {
            "validator_id": VALIDATOR_ID,
            "validator_version": VALIDATOR_VERSION,
            "certificate_artifact_id": "artifact.validation",
        },
        "requested_claim_status": "Computational Certificate",
        "negative_evidence": {
            "separation_statements": [
                "Image-rank collapse is not sector-pair word accessibility.",
                "Image-rank collapse is not route depth or Lie/Hall depth.",
                "A passing runtime validator is not upstream semantic acceptance.",
            ],
            "known_counterexample_refs": [],
            "failed_promotion_attempt_refs": [],
            "excluded_regimes": [
                "nondeterministic automata",
                "partial transition functions",
                "infinite state sets",
            ],
            "unsupported_policies": [
                "finite cutoff without exhaustive reachable-subset-orbit closure"
            ],
        },
    }
    validate_contract(
        package,
        RUNTIME_CONTRACT_ROOT / "promotion-package.schema.json",
        label="Promotion Package",
    )
    return package


def _validator_independence(request: dict[str, Any]) -> dict[str, Any]:
    return validator_independence(
        request, implementation_relation="separate_implementation"
    )


def run_rank_collapse(
    source: dict[str, Any],
    run_directory: str | Path,
    *,
    plugin: CarrierPlugin | None = None,
    policies: dict[str, Any] | None = None,
    execution_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    selected_plugin = plugin or RankCollapsePlugin()
    run_dir = Path(run_directory).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    request = build_rank_collapse_request(
        source,
        run_dir,
        plugin=selected_plugin,
        policies=policies,
        execution_id=execution_id,
        created_at=created_at,
    )
    store = ArtifactStore(run_dir, PROJECT_ROOT)

    source_path = write_json(run_dir / "source.json", source)
    request_path = write_json(run_dir / "run-request.json", request)
    source_artifact = store.put_json(
        source,
        artifact_id="artifact.source",
        role="source-input",
        schema_version=None,
    )
    request_artifact = store.put_json(
        request,
        artifact_id="artifact.run-request",
        role="source-data",
        schema_version="sof.run-request.v1",
    )
    outputs = [
        output_item(
            kind="source",
            convenience_path=source_path,
            artifact=source_artifact,
            schema_id=None,
            producer="automata-adapter@0.1.0",
            input_refs=[],
        ),
        output_item(
            kind="run_request",
            convenience_path=request_path,
            artifact=request_artifact,
            schema_id="sof.run-request.v1",
            producer="sof-runtime@0.1.0",
            input_refs=["artifact.source"],
        ),
    ]

    try:
        normalize_source(source)
        manifest = build_manifest(source)
        validate_contract(
            manifest,
            COMPILER_CONTRACT_ROOT / "capability-manifest.schema.json",
            label="Capability Manifest",
        )
    except (ContractError, ValueError) as error:
        response = _failure_response(
            request,
            status="FAILED_VALIDATION",
            stage="INPUT_VALIDATION",
            error=error,
            outputs=outputs,
        )
        write_json(run_dir / "run-response.json", response)
        return response

    manifest_path = write_json(run_dir / "manifest.json", manifest)
    outputs[0]["artifact_ref"]["schema_id"] = "rime.automata.source.v1"
    manifest_artifact = store.put_json(
        manifest,
        artifact_id="artifact.manifest",
        role="manifest",
        schema_version="1.0",
    )
    outputs.append(
        output_item(
            kind="manifest",
            convenience_path=manifest_path,
            artifact=manifest_artifact,
            schema_id="1.0",
            producer="automata-adapter@0.1.0",
            input_refs=["artifact.source"],
        )
    )

    if request["policies"] != SUPPORTED_POLICY:
        error = UnsupportedRankCollapsePolicy(
            "rank-collapse v1 supports only exhaustive reachable-subset-orbit policy"
        )
        response = _failure_response(
            request,
            status="UNSUPPORTED",
            stage="POLICY_ADMISSION",
            error=error,
            outputs=outputs,
        )
        write_json(run_dir / "run-response.json", response)
        return response

    try:
        bundle = selected_plugin.compute(request)
        _validate_rank_bundle(bundle)
    except UnsupportedRankCollapsePolicy as error:
        response = _failure_response(
            request,
            status="UNSUPPORTED",
            stage="POLICY_ADMISSION",
            error=error,
            outputs=outputs,
        )
        write_json(run_dir / "run-response.json", response)
        return response
    except PluginExecutionError as error:
        response = _failure_response(
            request,
            status="CANCELLED" if error.cancelled else "FAILED_EXECUTION",
            stage="CANCELLATION" if error.cancelled else "PLUGIN_EXECUTION",
            error=error,
            outputs=outputs,
            stderr=error.stderr,
            retryable=error.retryable,
        )
        write_json(run_dir / "run-response.json", response)
        return response
    except Exception as error:
        response = _failure_response(
            request,
            status="FAILED_EXECUTION",
            stage="PLUGIN_EXECUTION",
            error=error,
            outputs=outputs,
        )
        write_json(run_dir / "run-response.json", response)
        return response

    bundle_path = write_json(run_dir / "rank-collapse-bundle.json", bundle)
    bundle_artifact = store.put_json(
        bundle,
        artifact_id="artifact.rank-bundle",
        role="source-data",
        schema_version="rime.rank-collapse.bundle.v1",
    )
    bundle_output = output_item(
        kind="result_bundle",
        convenience_path=bundle_path,
        artifact=bundle_artifact,
        schema_id="rime.rank-collapse.bundle.v1",
        producer=f"{selected_plugin.plugin_id}@{selected_plugin.plugin_version}",
        input_refs=["artifact.source", "artifact.run-request"],
    )
    outputs.append(bundle_output)

    canonical_source = store.load_json(source_artifact)
    canonical_request = store.load_json(request_artifact)
    canonical_bundle = store.load_json(bundle_artifact)
    certificate = validate_rank_collapse(
        canonical_source,
        canonical_bundle,
        request=canonical_request,
        input_source="canonical_source_artifacts",
        validator_independence=_validator_independence(canonical_request),
    )
    validate_contract(
        certificate,
        RANK_COLLAPSE_CONTRACT_ROOT / "certificate.schema.json",
        label="rank-collapse certificate",
    )
    certificate_path = write_json(run_dir / "validation-certificate.json", certificate)
    validation_artifact = store.put_json(
        certificate,
        artifact_id="artifact.validation",
        role="validator-output",
        schema_version="rime.rank-collapse.certificate.v1",
    )
    validation_output = output_item(
        kind="validation_certificate",
        convenience_path=certificate_path,
        artifact=validation_artifact,
        schema_id="rime.rank-collapse.certificate.v1",
        producer=f"{VALIDATOR_ID}@{VALIDATOR_VERSION}",
        input_refs=["artifact.source", "artifact.run-request", "artifact.rank-bundle"],
    )
    outputs.append(validation_output)

    if certificate["status"] != "PASS":
        error = ValueError("rank-collapse independent validation failed")
        response = _failure_response(
            request,
            status="FAILED_VALIDATION",
            stage="INDEPENDENT_VALIDATION",
            error=error,
            outputs=outputs,
            validator_ran=True,
        )
        write_json(run_dir / "run-response.json", response)
        return response

    response = {
        "schema_id": "sof.run-response.v1",
        "semantic_run_id": request["semantic_run_id"],
        "execution_id": request["execution_id"],
        "request_digest": sha256_bytes(canonical_json_bytes(request)),
        "plugin": request["plugin"],
        "carrier_kind": "rank_collapse",
        "status": "SUCCEEDED",
        "artifact_directory": request["artifact_directory"],
        "outputs": outputs,
        "artifact_closure": build_artifact_closure(outputs),
        "validator": {
            "validator_id": VALIDATOR_ID,
            "validator_version": VALIDATOR_VERSION,
            "ran": True,
        },
        "failure": None,
        "diagnostics": [
            "rank-collapse bundle independently recomputed",
            "Typed SOF IR and Compiler Output require an upstream rank-collapse carrier contract",
        ],
    }
    validate_contract(
        response,
        RUNTIME_CONTRACT_ROOT / "run-response.schema.json",
        label="RunResponse",
    )
    write_json(run_dir / "run-response.json", response)
    response_artifact = store.put_json(
        response,
        artifact_id="artifact.run-response",
        role="adapter-output",
        schema_version="sof.run-response.v1",
    )
    response_ref = runtime_ref(
        response_artifact,
        schema_id="sof.run-response.v1",
        producer="sof-runtime@0.1.0",
        input_refs=[
            "artifact.run-request",
            "artifact.rank-bundle",
            "artifact.validation",
        ],
    )
    package_refs = [item["artifact_ref"] for item in outputs]
    promotion = _promotion_package(
        request,
        [*package_refs, response_ref],
        response["artifact_closure"]["artifact_manifest_digest"],
    )
    write_json(run_dir / "promotion-package.json", promotion)
    store.put_json(
        promotion,
        artifact_id="artifact.promotion-package",
        role="adapter-output",
        schema_version="sof.promotion-package.v1",
    )
    return response


def validate_run_response(response_path: str | Path) -> dict[str, Any]:
    response, outputs, request = verify_response_artifacts(response_path)

    if response["status"] != "SUCCEEDED":
        return response

    required = {
        "source",
        "manifest",
        "run_request",
        "result_bundle",
        "validation_certificate",
    }
    missing = sorted(required - set(outputs))
    if missing:
        raise ValueError("successful RunResponse is missing outputs: " + ", ".join(missing))
    if response["validator"] != {
        "validator_id": VALIDATOR_ID,
        "validator_version": VALIDATOR_VERSION,
        "ran": True,
    }:
        raise ValueError("RunResponse validator identity mismatch")

    source = load_json(PROJECT_ROOT / outputs["source"]["artifact_ref"]["uri"])
    bundle = load_json(PROJECT_ROOT / outputs["result_bundle"]["artifact_ref"]["uri"])
    certificate = load_json(
        PROJECT_ROOT / outputs["validation_certificate"]["artifact_ref"]["uri"]
    )
    recomputed = validate_rank_collapse(
        source,
        bundle,
        request=request,
        input_source="canonical_source_artifacts",
        validator_independence=_validator_independence(request),
    )
    if recomputed != certificate:
        raise ValueError("stored validation certificate differs from independent recomputation")
    if certificate["validator_id"] != VALIDATOR_ID or certificate["validator_version"] != VALIDATOR_VERSION:
        raise ValueError("validation certificate version mismatch")
    expected_digests = {
        "source": outputs["source"]["artifact_ref"]["sha256"],
        "bundle": outputs["result_bundle"]["artifact_ref"]["sha256"],
        "request": outputs["run_request"]["artifact_ref"]["sha256"],
        "policy": sha256_bytes(canonical_json_bytes(request["policies"])),
    }
    if certificate["input_digests"] != expected_digests:
        raise ValueError("validation certificate input digests do not bind run artifacts")

    return certificate


def validate_promotion_package(
    package_path: str | Path,
    response_path: str | Path,
) -> dict[str, Any]:
    validate_run_response(response_path)
    response = load_json(response_path)
    promotion = load_json(package_path)
    validate_contract(
        promotion,
        RUNTIME_CONTRACT_ROOT / "promotion-package.schema.json",
        label="Promotion Package",
    )
    if promotion["semantic_run_id"] != response["semantic_run_id"]:
        raise ValueError("Promotion Package semantic identity mismatch")
    if response["execution_id"] not in promotion["execution_ids"]:
        raise ValueError("Promotion Package omits the execution identity")

    verify_promotion_artifact_closure(promotion, response)

    package_bytes = canonical_json_bytes(promotion)
    package_digest = sha256_bytes(package_bytes)
    artifact_root = (PROJECT_ROOT / response["artifact_directory"]).resolve()
    package_artifact_path = artifact_root / package_digest[:2] / f"{package_digest}.json"
    if not package_artifact_path.is_file() or sha256_file(package_artifact_path) != package_digest:
        raise ValueError("Promotion Package artifact verification failed")
    return promotion
