from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import uuid4
import platform

from sof_runtime.artifacts import canonical_json_bytes, sha256_bytes


CANONICAL_JSON_PROFILE = "sof-cjson-v1"


def semantic_request_payload(
    *,
    source: dict[str, Any],
    plugin: dict[str, str],
    carrier_kind: str,
    contract_versions: dict[str, str],
    policies: dict[str, Any],
    semantic_environment: dict[str, Any],
) -> dict[str, Any]:
    return {
        "canonical_json_profile": CANONICAL_JSON_PROFILE,
        "carrier_kind": carrier_kind,
        "contract_versions": contract_versions,
        "plugin": plugin,
        "policies": policies,
        "semantic_environment": semantic_environment,
        "source": source,
    }


def compute_semantic_run_id(
    *,
    source: dict[str, Any],
    plugin: dict[str, str],
    carrier_kind: str,
    contract_versions: dict[str, str],
    policies: dict[str, Any],
    semantic_environment: dict[str, Any],
) -> str:
    payload = semantic_request_payload(
        source=source,
        plugin=plugin,
        carrier_kind=carrier_kind,
        contract_versions=contract_versions,
        policies=policies,
        semantic_environment=semantic_environment,
    )
    return "semrun:sha256:" + sha256_bytes(canonical_json_bytes(payload))


def new_execution_id(
    *,
    semantic_run_id: str,
    runtime_environment: dict[str, str],
    started_at: str,
) -> str:
    payload = {
        "semantic_run_id": semantic_run_id,
        "runtime_environment": runtime_environment,
        "started_at": started_at,
        "nonce": str(uuid4()),
    }
    return "exec:sha256:" + sha256_bytes(canonical_json_bytes(payload))


def semantic_environment_for(plugin: Any) -> dict[str, Any]:
    declared = getattr(plugin, "semantic_environment", None)
    if not isinstance(declared, dict):
        raise ValueError("plugin must declare a semantic_environment projection")
    return deepcopy(declared)


def runtime_environment_for(plugin: Any) -> dict[str, str]:
    language = getattr(plugin, "implementation_language", "unknown")
    runtime_family = (
        platform.python_implementation().lower()
        if language == "python"
        else "external"
    )
    return {
        "execution_mode": getattr(plugin, "execution_mode", "unknown"),
        "implementation_language": language,
        "runtime_family": runtime_family,
        "runtime_version": (
            platform.python_version() if language == "python" else "external"
        ),
        "operating_system": platform.system().lower() or "unknown",
        "machine_architecture": platform.machine().lower() or "unknown",
    }


def verify_semantic_run_id(request: dict[str, Any]) -> bool:
    expected = compute_semantic_run_id(
        source=request["source"],
        plugin=request["plugin"],
        carrier_kind=request["carrier_kind"],
        contract_versions=request["contract_versions"],
        policies=request["policies"],
        semantic_environment=request["semantic_environment"],
    )
    return request["semantic_run_id"] == expected
