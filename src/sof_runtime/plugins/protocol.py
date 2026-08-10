from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Protocol

from sof_runtime.artifacts import canonical_json_bytes
from sof_runtime.contracts import ContractError, loads_json, validate_contract
from sof_runtime.paths import RUNTIME_CONTRACT_ROOT


class CarrierPlugin(Protocol):
    plugin_id: str
    plugin_version: str
    carrier_kind: str
    contract_version: str
    semantic_environment: dict[str, Any]

    def compute(self, request: dict[str, Any]) -> dict[str, Any]: ...


class PluginExecutionError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        stderr: bytes = b"",
        retryable: bool = False,
        cancelled: bool = False,
    ):
        super().__init__(message)
        self.stderr = stderr
        self.retryable = retryable
        self.cancelled = cancelled


class ExternalPluginRunner:
    """Run an executable plugin that maps one RunRequest to one result payload."""

    def __init__(
        self,
        command: list[str],
        *,
        plugin_id: str = "external.plugin",
        plugin_version: str = "0.0.0",
        carrier_kind: str = "external",
        contract_version: str = "1.0",
        implementation_language: str = "unknown",
        semantic_environment: dict[str, Any] | None = None,
    ):
        if not command:
            raise ValueError("external plugin command cannot be empty")
        self.command = command
        self.plugin_id = plugin_id
        self.plugin_version = plugin_version
        self.carrier_kind = carrier_kind
        self.contract_version = contract_version
        self.execution_mode = "external_executable"
        self.implementation_language = implementation_language
        self.semantic_environment = semantic_environment or {
            "algorithm_mode": "externally_declared",
            "arithmetic_backend": "externally_declared",
            "dependency_lock_digest": None,
            "feature_flags": [],
        }

    def compute(
        self,
        request: dict[str, Any],
        *,
        cwd: str | Path | None = None,
        timeout: float = 300.0,
    ) -> dict[str, Any]:
        validate_contract(
            request,
            RUNTIME_CONTRACT_ROOT / "run-request.schema.json",
            label="RunRequest",
        )
        try:
            result = subprocess.run(
                self.command,
                input=canonical_json_bytes(request),
                capture_output=True,
                cwd=cwd,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as error:
            stderr = error.stderr if isinstance(error.stderr, bytes) else b""
            raise PluginExecutionError(
                f"external plugin timed out after {timeout} seconds",
                stderr=stderr,
                retryable=True,
                cancelled=True,
            ) from error
        if result.returncode != 0:
            raise PluginExecutionError(
                f"external plugin failed with exit {result.returncode}",
                stderr=result.stderr,
                retryable=False,
            )
        try:
            payload = loads_json(result.stdout.decode("utf-8"))
        except (UnicodeDecodeError, ContractError, ValueError) as error:
            raise PluginExecutionError(
                "external plugin did not emit one UTF-8 JSON payload",
                stderr=result.stderr,
            ) from error
        mismatched = [
            field
            for field in ("semantic_run_id", "execution_id")
            if payload.get(field) != request[field]
        ]
        if mismatched:
            raise PluginExecutionError(
                "external payload does not match RunRequest fields: "
                + ", ".join(mismatched),
                stderr=result.stderr,
            )
        return payload

    def run(
        self,
        request: dict[str, Any],
        *,
        cwd: str | Path | None = None,
        timeout: float = 300.0,
    ) -> dict[str, Any]:
        return self.compute(request, cwd=cwd, timeout=timeout)
