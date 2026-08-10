from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sof_runtime.adapters.markov import build_manifest, normalize_source
from sof_runtime.artifacts import ArtifactStore, canonical_json_bytes, sha256_bytes, sha256_file
from sof_runtime.carriers.positive_word_support import (
    SUPPORTED_POLICY,
    PositiveWordSupportPlugin,
    UnsupportedPositiveWordPolicy,
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
    POSITIVE_WORD_CONTRACT_ROOT,
    PROJECT_ROOT,
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
from sof_runtime.validation.positive_word_support import (
    VALIDATOR_ID,
    VALIDATOR_VERSION,
    validate_positive_word_support,
)


CONTRACT_VERSIONS = {
    "canonical_json": CANONICAL_JSON_PROFILE,
    "runtime": "1.0",
    "source": "rime.markov.source.v1",
    "extension": "rime.positive-word-support.bundle.v1",
}


def build_positive_word_request(
    source: dict[str, Any],
    run_directory: str | Path,
    *,
    plugin: CarrierPlugin | None = None,
    policies: dict[str, Any] | None = None,
    execution_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    selected_plugin = plugin or PositiveWordSupportPlugin()
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
    environment = runtime_environment_for(selected_plugin)
    semantic_environment = semantic_environment_for(selected_plugin)
    semantic_run_id = compute_semantic_run_id(
        source=source,
        plugin=plugin_identity,
        carrier_kind="positive_word_support",
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
            runtime_environment=environment,
            started_at=timestamp,
        ),
        "created_at": timestamp,
        "plugin": plugin_identity,
        "carrier_kind": "positive_word_support",
        "contract_versions": CONTRACT_VERSIONS,
        "semantic_environment": semantic_environment,
        "runtime_environment": environment,
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


def _validate_bundle(bundle: dict[str, Any]) -> None:
    validate_contract(
        bundle,
        POSITIVE_WORD_CONTRACT_ROOT / "bundle.schema.json",
        label="positive-word bundle",
    )
    validate_contract(
        bundle["object"],
        POSITIVE_WORD_CONTRACT_ROOT / "object.schema.json",
        label="positive-word object",
    )
    for item in bundle["findings"]:
        validate_contract(
            item["envelope"],
            RUNTIME_CONTRACT_ROOT / "finding-envelope.schema.json",
            label="finding envelope",
        )
        validate_contract(
            item["payload"],
            POSITIVE_WORD_CONTRACT_ROOT / "finding.schema.json",
            label="positive-word finding",
        )


def _promotion_package(
    request: dict[str, Any],
    artifact_refs: list[dict[str, Any]],
    artifact_closure_digest: str,
) -> dict[str, Any]:
    package = {
        "schema_id": "sof.promotion-package.v1",
        "package_id": "promotion:positive-word-support:"
        + request["semantic_run_id"].split(":")[-1],
        "promotion_state": "CANDIDATE",
        "semantic_run_id": request["semantic_run_id"],
        "execution_ids": [request["execution_id"]],
        "run_response_artifact_closure_digest": artifact_closure_digest,
        "candidate": {
            "extension_id": "positive-word-support",
            "extension_version": "1.0",
            "proposed_carrier_kind": "single_letter_positive_word_support",
            "semantics": "Ordered off-diagonal first-hit support depth for positive powers of one nonnegative operator.",
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
                "Positive-word support first hit is not Markov mixing time.",
                "Positive-word support first hit is not rank collapse or route depth.",
                "Nonnegative one-letter support does not justify signed or multi-letter cancellation claims.",
            ],
            "known_counterexample_refs": [],
            "failed_promotion_attempt_refs": [],
            "excluded_regimes": [
                "signed matrices",
                "multiple operative letters or their linear combinations",
                "complex weights",
                "route-sum cancellation",
                "tolerance-relative near-zero tests",
                "time-inhomogeneous transition families",
            ],
            "unsupported_policies": [
                "finite cutoff without exhaustive Boolean support closure"
            ],
        },
    }
    validate_contract(
        package,
        RUNTIME_CONTRACT_ROOT / "promotion-package.schema.json",
        label="Promotion Package",
    )
    return package


def _write_failure(
    run_dir: Path,
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
    response = failure_response(
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
    write_json(run_dir / "run-response.json", response)
    return response


def run_positive_word_support(
    source: dict[str, Any],
    run_directory: str | Path,
    *,
    plugin: CarrierPlugin | None = None,
    policies: dict[str, Any] | None = None,
    execution_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    selected_plugin = plugin or PositiveWordSupportPlugin()
    run_dir = Path(run_directory).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    request = build_positive_word_request(
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
            producer="markov-positive-word-adapter@0.1.0",
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
        return _write_failure(
            run_dir,
            request,
            status="FAILED_VALIDATION",
            stage="INPUT_VALIDATION",
            error=error,
            outputs=outputs,
        )

    outputs[0]["artifact_ref"]["schema_id"] = "rime.markov.source.v1"
    manifest_path = write_json(run_dir / "manifest.json", manifest)
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
            producer="markov-positive-word-adapter@0.1.0",
            input_refs=["artifact.source"],
        )
    )
    if request["policies"] != SUPPORTED_POLICY:
        return _write_failure(
            run_dir,
            request,
            status="UNSUPPORTED",
            stage="POLICY_ADMISSION",
            error=UnsupportedPositiveWordPolicy(
                "positive-word-support v1 supports only exhaustive off-diagonal pair scope"
            ),
            outputs=outputs,
        )
    try:
        bundle = selected_plugin.compute(request)
        _validate_bundle(bundle)
    except UnsupportedPositiveWordPolicy as error:
        return _write_failure(
            run_dir,
            request,
            status="UNSUPPORTED",
            stage="POLICY_ADMISSION",
            error=error,
            outputs=outputs,
        )
    except PluginExecutionError as error:
        return _write_failure(
            run_dir,
            request,
            status="CANCELLED" if error.cancelled else "FAILED_EXECUTION",
            stage="CANCELLATION" if error.cancelled else "PLUGIN_EXECUTION",
            error=error,
            outputs=outputs,
            stderr=error.stderr,
            retryable=error.retryable,
        )
    except Exception as error:
        return _write_failure(
            run_dir,
            request,
            status="FAILED_EXECUTION",
            stage="PLUGIN_EXECUTION",
            error=error,
            outputs=outputs,
        )

    bundle_path = write_json(run_dir / "positive-word-bundle.json", bundle)
    bundle_artifact = store.put_json(
        bundle,
        artifact_id="artifact.positive-word-bundle",
        role="source-data",
        schema_version="rime.positive-word-support.bundle.v1",
    )
    outputs.append(
        output_item(
            kind="result_bundle",
            convenience_path=bundle_path,
            artifact=bundle_artifact,
            schema_id="rime.positive-word-support.bundle.v1",
            producer=f"{selected_plugin.plugin_id}@{selected_plugin.plugin_version}",
            input_refs=["artifact.source", "artifact.run-request"],
        )
    )
    canonical_source = store.load_json(source_artifact)
    canonical_request = store.load_json(request_artifact)
    canonical_bundle = store.load_json(bundle_artifact)
    independence = validator_independence(
        canonical_request, implementation_relation="separate_algorithm"
    )
    certificate = validate_positive_word_support(
        canonical_source,
        canonical_bundle,
        request=canonical_request,
        validator_independence=independence,
    )
    validate_contract(
        certificate,
        POSITIVE_WORD_CONTRACT_ROOT / "certificate.schema.json",
        label="positive-word certificate",
    )
    certificate_path = write_json(run_dir / "validation-certificate.json", certificate)
    certificate_artifact = store.put_json(
        certificate,
        artifact_id="artifact.validation",
        role="validator-output",
        schema_version="rime.positive-word-support.certificate.v1",
    )
    outputs.append(
        output_item(
            kind="validation_certificate",
            convenience_path=certificate_path,
            artifact=certificate_artifact,
            schema_id="rime.positive-word-support.certificate.v1",
            producer=f"{VALIDATOR_ID}@{VALIDATOR_VERSION}",
            input_refs=[
                "artifact.source",
                "artifact.run-request",
                "artifact.positive-word-bundle",
            ],
        )
    )
    if certificate["status"] != "PASS":
        return _write_failure(
            run_dir,
            request,
            status="FAILED_VALIDATION",
            stage="INDEPENDENT_VALIDATION",
            error=ValueError("positive-word independent validation failed"),
            outputs=outputs,
            validator_ran=True,
        )

    response = {
        "schema_id": "sof.run-response.v1",
        "semantic_run_id": request["semantic_run_id"],
        "execution_id": request["execution_id"],
        "request_digest": sha256_bytes(canonical_json_bytes(request)),
        "plugin": request["plugin"],
        "carrier_kind": request["carrier_kind"],
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
            "positive-word support recomputed by Floyd-Warshall closure",
            "no mixing-time, rank-collapse, route-depth, or Lie/Hall claim emitted",
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
            "artifact.positive-word-bundle",
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


def validate_positive_word_response(response_path: str | Path) -> dict[str, Any]:
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
    recomputed = validate_positive_word_support(
        source,
        bundle,
        request=request,
        validator_independence=validator_independence(
            request, implementation_relation="separate_algorithm"
        ),
    )
    if recomputed != certificate:
        raise ValueError("stored positive-word certificate differs from recomputation")
    expected_digests = {
        "source": outputs["source"]["artifact_ref"]["sha256"],
        "bundle": outputs["result_bundle"]["artifact_ref"]["sha256"],
        "request": outputs["run_request"]["artifact_ref"]["sha256"],
        "policy": sha256_bytes(canonical_json_bytes(request["policies"])),
    }
    if certificate["input_digests"] != expected_digests:
        raise ValueError("positive-word certificate input digests do not bind artifacts")
    return certificate


def validate_positive_word_promotion(
    package_path: str | Path, response_path: str | Path
) -> dict[str, Any]:
    validate_positive_word_response(response_path)
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
    package_digest = sha256_bytes(canonical_json_bytes(promotion))
    artifact_root = (PROJECT_ROOT / response["artifact_directory"]).resolve()
    package_artifact = artifact_root / package_digest[:2] / f"{package_digest}.json"
    if not package_artifact.is_file() or sha256_file(package_artifact) != package_digest:
        raise ValueError("Promotion Package artifact verification failed")
    return promotion
