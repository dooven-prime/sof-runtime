"""Transport-neutral orchestration over the stable RuntimeAPI facade."""

from __future__ import annotations

import base64
import mimetypes
import re
import shutil
from pathlib import Path
from threading import RLock
from typing import Any, Callable
from urllib.parse import urlparse

from sof_runtime import __version__
from sof_runtime.action import validate_action, validate_action_validation_receipt
from sof_runtime.api import Comparison, Realization, Report, RuntimeAPI
from sof_runtime.artifacts import canonical_json_bytes, sha256_bytes, sha256_file
from sof_runtime.comparison import validate_audit, validate_audit_validation_receipt
from sof_runtime.contracts import ContractError, load_json, validate_contract
from sof_runtime.explain import explain_run
from sof_runtime.paths import CONTRACTS_ROOT, PROJECT_ROOT, SERVICE_CONTRACT_ROOT
from sof_runtime.reporting import validate_receipt, validate_report

from .jobs import JobStore
from .lifecycle import JobLifecycle
from .workspace import WorkspaceManager, WorkspaceViolation


SERVICE_PRODUCER = f"sof-runtime.service@{__version__}"
SERVICE_CONTRACT_NAMES = frozenset(
    {
        "service-request.schema.json",
        "service-response.schema.json",
        "service-error.schema.json",
        "job.schema.json",
    }
)

_QUOTED_ABSOLUTE_PATH = re.compile(
    r'''(?P<quote>["'])(?:[A-Za-z]:[\\/]|\\\\[^\\/\s]+[\\/][^\\/\s]+[\\/]|/)'''
    r'''[^"'\r\n]*(?P=quote)'''
)
_WINDOWS_ABSOLUTE_PATH = re.compile(
    r'''(?<![A-Za-z0-9_:/.-])(?:[A-Za-z]:[\\/]|\\\\[^\\/\s]+[\\/][^\\/\s]+[\\/])'''
    r'''[^\s"'<>|]*'''
)
_POSIX_ABSOLUTE_PATH = re.compile(
    r'''(?<![A-Za-z0-9_:/.-])/(?:[^/\s"'<>]+/)+[^\s"'<>]*'''
)


def _sanitize_public_message(message: str) -> str:
    """Redact embedded host paths without interpreting the surrounding message."""
    sanitized = _QUOTED_ABSOLUTE_PATH.sub(
        lambda match: f"{match.group('quote')}<server-path>{match.group('quote')}",
        message,
    )
    sanitized = _WINDOWS_ABSOLUTE_PATH.sub("<server-path>", sanitized)
    return _POSIX_ABSOLUTE_PATH.sub("<server-path>", sanitized)


class ServiceError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        request_id: str | None = None,
        job_id: str | None = None,
        details: list[str] | None = None,
    ):
        public_message = _sanitize_public_message(message)
        public_details = [
            _sanitize_public_message(detail) for detail in (details or [])
        ]
        super().__init__(public_message)
        self.payload = {
            "contract_id": "sof-runtime.service-error.v1",
            "request_id": request_id,
            "job_id": job_id,
            "code": code,
            "message": public_message,
            "details": public_details,
        }


def _json_schema_id(path: Path) -> str | None:
    if path.suffix.lower() != ".json":
        return None
    try:
        payload = load_json(path)
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    value = payload.get("schema_id") or payload.get("contract_id")
    return value if isinstance(value, str) else None


class ServiceApplication:
    """Own orchestration only; scientific operations delegate to stable APIs."""

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        runtime: RuntimeAPI | None = None,
    ):
        self.workspaces = WorkspaceManager(workspace_root)
        self.runtime = runtime or RuntimeAPI()
        self.jobs = JobStore(self.workspaces)
        self.lifecycle = JobLifecycle(self.jobs)
        self.execution_cache = PROJECT_ROOT / "runs" / ".sof-service-cache"
        self.execution_cache.mkdir(parents=True, exist_ok=True)
        self._execution_lock = RLock()

    def execute(self, request: dict[str, Any]) -> dict[str, Any]:
        request_id = request.get("request_id") if isinstance(request, dict) else None
        try:
            validate_contract(
                request,
                SERVICE_CONTRACT_ROOT / "service-request.schema.json",
                label="service request",
            )
        except (ContractError, TypeError) as error:
            raise self._error("invalid_request", str(error), request_id=request_id) from error

        job = self.lifecycle.begin(request)
        try:
            semantic_run_id = self._semantic_run_id(request)
            execution_directory = self._execution_directory(
                semantic_run_id,
                request["operation"],
            )
            with self._execution_lock:
                result, artifact_paths = getattr(self, f"_{request['operation']}")(
                    request["workspace_id"],
                    _execution_directory=execution_directory,
                    **request["input"],
                )
            result = self._public_projection(request["workspace_id"], result)
            response = {
                "contract_id": "sof-runtime.service-response.v1",
                "request_id": request["request_id"],
                "job_id": job["job_id"],
                "semantic_run_id": semantic_run_id,
                "workspace_id": request["workspace_id"],
                "operation": request["operation"],
                "status": "succeeded",
                "result": result,
                "artifacts": [
                    self._artifact_ref(request["workspace_id"], role, path)
                    for role, path in artifact_paths
                ],
            }
            validate_contract(
                response,
                SERVICE_CONTRACT_ROOT / "service-response.schema.json",
                label="service response",
            )
            self.lifecycle.succeed(job, response)
            return response
        except ServiceError as error:
            error.payload = self._public_projection(
                request["workspace_id"], error.payload
            )
            error.payload["job_id"] = job["job_id"]
            self.lifecycle.fail(job, error.payload)
            raise
        except FileNotFoundError as error:
            service_error = self._error(
                "not_found",
                self._public_projection(request["workspace_id"], str(error)),
                request_id=request["request_id"],
                job_id=job["job_id"],
            )
            self.lifecycle.fail(job, service_error.payload)
            raise service_error from error
        except WorkspaceViolation as error:
            service_error = self._error(
                "path_violation",
                self._public_projection(request["workspace_id"], str(error)),
                request_id=request["request_id"],
                job_id=job["job_id"],
            )
            self.lifecycle.fail(job, service_error.payload)
            raise service_error from error
        except Exception as error:
            service_error = self._error(
                "execution_failed",
                self._public_projection(request["workspace_id"], str(error)),
                request_id=request["request_id"],
                job_id=job["job_id"],
            )
            self.lifecycle.fail(job, service_error.payload)
            raise service_error from error

    def execute_operation(
        self,
        operation: str,
        workspace_id: str,
        operation_input: dict[str, Any],
        *,
        request_id: str,
    ) -> dict[str, Any]:
        return self.execute(
            {
                "contract_id": "sof-runtime.service-request.v1",
                "request_id": request_id,
                "workspace_id": workspace_id,
                "operation": operation,
                "input": operation_input,
            }
        )

    def realize(
        self,
        workspace_id: str,
        case_directory: str,
        run_directory: str,
        *,
        request_id: str,
    ) -> dict[str, Any]:
        return self.execute_operation(
            "realize",
            workspace_id,
            {"case_directory": case_directory, "run_directory": run_directory},
            request_id=request_id,
        )

    def report(
        self,
        workspace_id: str,
        realization_run_directory: str,
        out_directory: str,
        *,
        compiler_profile: str | None = None,
        assembly_profile: str | None = None,
        request_id: str,
    ) -> dict[str, Any]:
        operation_input = {
            "realization_run_directory": realization_run_directory,
            "out_directory": out_directory,
        }
        if compiler_profile is not None:
            operation_input["compiler_profile"] = compiler_profile
        if assembly_profile is not None:
            operation_input["assembly_profile"] = assembly_profile
        return self.execute_operation(
            "report", workspace_id, operation_input, request_id=request_id
        )

    def compare(
        self,
        workspace_id: str,
        reference: dict[str, str],
        target: dict[str, str],
        alignment: str,
        comparison_profile: str,
        out_directory: str,
        *,
        request_id: str,
    ) -> dict[str, Any]:
        return self.execute_operation(
            "compare",
            workspace_id,
            {
                "reference": reference,
                "target": target,
                "alignment": alignment,
                "comparison_profile": comparison_profile,
                "out_directory": out_directory,
            },
            request_id=request_id,
        )

    def interpret(
        self,
        workspace_id: str,
        audit: str,
        receipt: str,
        context: str,
        policy: str,
        out_directory: str,
        *,
        request_id: str,
    ) -> dict[str, Any]:
        return self.execute_operation(
            "interpret",
            workspace_id,
            {
                "audit": audit,
                "receipt": receipt,
                "context": context,
                "policy": policy,
                "out_directory": out_directory,
            },
            request_id=request_id,
        )

    def validate(
        self,
        workspace_id: str,
        validation_kind: str,
        artifact: str,
        *,
        request_id: str,
    ) -> dict[str, Any]:
        return self.execute_operation(
            "validate",
            workspace_id,
            {"validation_kind": validation_kind, "artifact": artifact},
            request_id=request_id,
        )

    def explain(
        self,
        workspace_id: str,
        run_directory: str,
        *,
        request_id: str,
    ) -> dict[str, Any]:
        return self.execute_operation(
            "explain",
            workspace_id,
            {"run_directory": run_directory},
            request_id=request_id,
        )

    def _realize(
        self,
        workspace_id: str,
        *,
        case_directory: str,
        run_directory: str,
        _execution_directory: Path | None = None,
    ) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        destination = self.workspaces.resolve(workspace_id, run_directory)
        execution_directory = _execution_directory or destination
        case_path = self._stage_case(
            workspace_id,
            case_directory,
            execution_directory / "inputs" / "case-bundle",
        )
        realization = self.runtime.realize(
            case_path,
            execution_directory,
        )
        if execution_directory != destination:
            self._mirror(execution_directory, destination)
            realization = Realization(
                source_id=realization.source_id,
                eligibility=realization.eligibility,
                candidate_path=(
                    destination
                    / realization.candidate_path.relative_to(execution_directory)
                ),
                declaration_path=(
                    destination
                    / realization.declaration_path.relative_to(execution_directory)
                ),
                inspection_path=(
                    destination
                    / realization.inspection_path.relative_to(execution_directory)
                ),
                evidence_path=(
                    destination
                    / realization.evidence_path.relative_to(execution_directory)
                ),
                run_receipt_path=(
                    destination
                    / realization.run_receipt_path.relative_to(execution_directory)
                ),
            )
        return (
            {
                "source_id": realization.source_id,
                "eligibility": realization.eligibility,
                "canonical_compilable": realization.canonical_compilable,
            },
            [
                ("realization_candidate", realization.candidate_path),
                ("adapter_declaration", realization.declaration_path),
                ("source_inspection", realization.inspection_path),
                ("realization_evidence", realization.evidence_path),
                ("realization_receipt", realization.run_receipt_path),
            ],
        )

    def _report(
        self,
        workspace_id: str,
        *,
        realization_run_directory: str,
        out_directory: str,
        compiler_profile: str | None = None,
        assembly_profile: str | None = None,
        _execution_directory: Path | None = None,
    ) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        destination = self.workspaces.resolve(workspace_id, out_directory)
        execution_directory = _execution_directory or destination
        realization = self.runtime.load_realization(
            self.workspaces.resolve(
                workspace_id, realization_run_directory, must_exist=True
            )
        )
        compiler_profile_path = (
            self._stage_file(
                self.workspaces.resolve(
                    workspace_id, compiler_profile, must_exist=True
                ),
                execution_directory / "inputs" / "compiler-profile.json",
            )
            if compiler_profile is not None
            else None
        )
        assembly_profile_path = (
            self._stage_file(
                self.workspaces.resolve(
                    workspace_id, assembly_profile, must_exist=True
                ),
                execution_directory / "inputs" / "assembly-profile.json",
            )
            if assembly_profile is not None
            else None
        )
        report = self.runtime.report(
            realization,
            execution_directory,
            compiler_profile_path=compiler_profile_path,
            assembly_profile_path=assembly_profile_path,
        )
        if execution_directory != destination:
            self._mirror(execution_directory, destination)
            report = Report(
                report_id=report.report_id,
                artifact_path=destination / report.artifact_path.relative_to(execution_directory),
                validation_receipt_path=(
                    destination
                    / report.validation_receipt_path.relative_to(execution_directory)
                ),
            )
        return (
            {"report_id": report.report_id},
            [
                ("sofrs_report", report.artifact_path),
                ("sofrs_validation_receipt", report.validation_receipt_path),
            ],
        )

    def _compare(
        self,
        workspace_id: str,
        *,
        reference: dict[str, str],
        target: dict[str, str],
        alignment: str,
        comparison_profile: str,
        out_directory: str,
        _execution_directory: Path | None = None,
    ) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        destination = self.workspaces.resolve(workspace_id, out_directory)
        execution_directory = _execution_directory or destination
        reference_handle = self._staged_report_handle(
            workspace_id,
            reference,
            execution_directory / "inputs" / "reference",
        )
        target_handle = self._staged_report_handle(
            workspace_id,
            target,
            execution_directory / "inputs" / "target",
        )
        alignment_path = self._stage_file(
            self.workspaces.resolve(workspace_id, alignment, must_exist=True),
            execution_directory / "inputs" / "alignment.json",
        )
        profile_path = self._stage_file(
            self.workspaces.resolve(
                workspace_id, comparison_profile, must_exist=True
            ),
            execution_directory / "inputs" / "comparison-profile.json",
        )
        comparison = self.runtime.compare(
            reference_handle,
            target_handle,
            alignment=alignment_path,
            profile=profile_path,
            out_dir=execution_directory / "output",
        )
        if execution_directory != destination:
            self._mirror(execution_directory / "output", destination)
            comparison = Comparison(
                audit_id=comparison.audit_id,
                artifact_path=(
                    destination
                    / comparison.artifact_path.relative_to(execution_directory / "output")
                ),
                validation_receipt_path=(
                    destination
                    / comparison.validation_receipt_path.relative_to(
                        execution_directory / "output"
                    )
                ),
            )
        return (
            {"audit_id": comparison.audit_id},
            [
                ("sofaudit", comparison.artifact_path),
                ("sofaudit_validation_receipt", comparison.validation_receipt_path),
            ],
        )

    def _interpret(
        self,
        workspace_id: str,
        *,
        audit: str,
        receipt: str,
        context: str,
        policy: str,
        out_directory: str,
        _execution_directory: Path | None = None,
    ) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        destination = self.workspaces.resolve(workspace_id, out_directory)
        execution_directory = _execution_directory or destination
        audit_path = self._stage_file(
            self.workspaces.resolve(workspace_id, audit, must_exist=True),
            execution_directory / "inputs" / "audit.json",
        )
        receipt_path = self._stage_file(
            self.workspaces.resolve(workspace_id, receipt, must_exist=True),
            execution_directory / "inputs" / "audit-receipt.json",
        )
        context_path = self._stage_file(
            self.workspaces.resolve(workspace_id, context, must_exist=True),
            execution_directory / "inputs" / "context.json",
        )
        policy_path = self._stage_file(
            self.workspaces.resolve(workspace_id, policy, must_exist=True),
            execution_directory / "inputs" / "policy.json",
        )
        audit_payload = load_json(audit_path)
        comparison = Comparison(
            audit_id=audit_payload["audit_id"],
            artifact_path=audit_path,
            validation_receipt_path=receipt_path,
        )
        interpretation, candidates = self.runtime.interpret(
            comparison,
            context_path,
            policy_path,
            execution_directory / "output",
        )
        if execution_directory != destination:
            self._mirror(execution_directory / "output", destination)
            interpretation = type(interpretation)(
                action_record_id=interpretation.action_record_id,
                artifact_path=(
                    destination
                    / interpretation.artifact_path.relative_to(
                        execution_directory / "output"
                    )
                ),
                validation_receipt_path=(
                    destination
                    / interpretation.validation_receipt_path.relative_to(
                        execution_directory / "output"
                    )
                ),
            )
            candidates = tuple(
                type(candidate)(
                    action_id=candidate.action_id,
                    disposition=candidate.disposition,
                    artifact_path=interpretation.artifact_path,
                    validation_receipt_path=interpretation.validation_receipt_path,
                )
                for candidate in candidates
            )
        return (
            {
                "action_record_id": interpretation.action_record_id,
                "candidate_actions": [
                    {"action_id": item.action_id, "disposition": item.disposition}
                    for item in candidates
                ],
            },
            [
                ("sofaction", interpretation.artifact_path),
                ("sofaction_validation_receipt", interpretation.validation_receipt_path),
            ],
        )

    def _validate(
        self,
        workspace_id: str,
        *,
        validation_kind: str,
        artifact: str,
        _execution_directory: Path | None = None,
    ) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        path = self.workspaces.resolve(workspace_id, artifact, must_exist=True)
        validators: dict[str, Callable[..., dict[str, Any]]] = {
            "sofrs": validate_report,
            "sofrs_receipt": validate_receipt,
            "sofaudit": validate_audit,
            "sofaudit_receipt": validate_audit_validation_receipt,
            "sofaction": validate_action,
            "sofaction_receipt": validate_action_validation_receipt,
        }
        result = validators[validation_kind](path, repository_root=PROJECT_ROOT)
        return (
            {"validation_kind": validation_kind, "validator_result": result},
            [(validation_kind, path)],
        )

    def _explain(
        self,
        workspace_id: str,
        *,
        run_directory: str,
        _execution_directory: Path | None = None,
    ) -> tuple[dict[str, Any], list[tuple[str, Path]]]:
        run = self.workspaces.resolve(workspace_id, run_directory, must_exist=True)
        return ({"explanation": explain_run(run)}, [])

    def _public_projection(self, workspace_id: str, value: Any) -> Any:
        """Remove host filesystem identities from transport-facing values."""
        if isinstance(value, dict):
            return {
                key: self._public_projection(workspace_id, item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [self._public_projection(workspace_id, item) for item in value]
        if not isinstance(value, str) or "://" in value:
            return value
        path = Path(value)
        if not path.is_absolute():
            return value
        resolved = path.resolve()
        try:
            relative = self.workspaces.relative(workspace_id, resolved)
            return f"sof-workspace://{workspace_id}/{relative}"
        except WorkspaceViolation:
            pass
        try:
            return resolved.relative_to(PROJECT_ROOT).as_posix()
        except ValueError:
            return f"<server-path>/{resolved.name}"

    def get_job(self, workspace_id: str, job_id: str) -> dict[str, Any]:
        try:
            return self.jobs.get(workspace_id, job_id)
        except (FileNotFoundError, WorkspaceViolation) as error:
            raise self._error(
                "not_found",
                self._public_projection(workspace_id, str(error)),
                job_id=job_id,
            ) from error

    def get_contract(self, contract_name: str) -> dict[str, Any]:
        """Return one frozen service envelope contract without creating a job."""
        if contract_name not in SERVICE_CONTRACT_NAMES:
            raise self._error("not_found", "unknown service contract")
        path = SERVICE_CONTRACT_ROOT / contract_name
        return {
            "contract_name": contract_name,
            "media_type": "application/schema+json",
            "sha256": sha256_file(path),
            "schema_id": _json_schema_id(path),
            "content": load_json(path),
        }

    def get_artifact(
        self,
        workspace_id: str,
        relative_path: str,
        sha256: str,
    ) -> dict[str, Any]:
        try:
            path = self.resolve_artifact(workspace_id, relative_path)
        except FileNotFoundError as error:
            raise self._error(
                "not_found",
                self._public_projection(workspace_id, str(error)),
            ) from error
        except WorkspaceViolation as error:
            raise self._error(
                "path_violation",
                self._public_projection(workspace_id, str(error)),
            ) from error
        actual = sha256_file(path)
        if actual != sha256:
            raise self._error("execution_failed", "artifact digest mismatch")
        media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        data = path.read_bytes()
        if media_type == "application/json":
            content: Any = load_json(path)
            encoding = "json"
        else:
            content = base64.b64encode(data).decode("ascii")
            encoding = "base64"
        return {
            "artifact": self._artifact_ref(workspace_id, "retrieved_artifact", path),
            "content_encoding": encoding,
            "content": content,
        }

    def resolve_artifact(self, workspace_id: str, locator: str) -> Path:
        if locator.startswith("sof-workspace://"):
            parsed = urlparse(locator)
            if parsed.netloc != workspace_id:
                raise WorkspaceViolation("artifact URI names a different workspace")
            return self.workspaces.resolve(
                workspace_id,
                parsed.path.lstrip("/"),
                must_exist=True,
            )

        candidate = (PROJECT_ROOT / locator).resolve()
        try:
            candidate.relative_to(self.execution_cache.resolve())
        except ValueError:
            return self.workspaces.resolve(workspace_id, locator, must_exist=True)
        if not candidate.is_file():
            raise FileNotFoundError(candidate)
        return candidate

    def _report_handle(self, workspace_id: str, value: dict[str, str]) -> Report:
        report_path = self.workspaces.resolve(
            workspace_id, value["report"], must_exist=True
        )
        payload = load_json(report_path)
        return Report(
            report_id=payload["report_id"],
            artifact_path=report_path,
            validation_receipt_path=self.workspaces.resolve(
                workspace_id, value["receipt"], must_exist=True
            ),
        )

    def _staged_report_handle(
        self,
        workspace_id: str,
        value: dict[str, str],
        destination: Path,
    ) -> Report:
        source = self._report_handle(workspace_id, value)
        report_path = self._stage_file(
            source.artifact_path,
            destination / "report.json",
        )
        receipt_path = self._stage_file(
            source.validation_receipt_path,
            destination / "receipt.json",
        )
        return Report(
            report_id=source.report_id,
            artifact_path=report_path,
            validation_receipt_path=receipt_path,
        )

    def _artifact_ref(self, workspace_id: str, role: str, path: Path) -> dict[str, Any]:
        digest = sha256_file(path)
        try:
            uri = (
                f"sof-workspace://{workspace_id}/"
                f"{self.workspaces.relative(workspace_id, path)}"
            )
        except WorkspaceViolation:
            resolved = path.resolve()
            try:
                resolved.relative_to(self.execution_cache.resolve())
            except ValueError as error:
                raise WorkspaceViolation(
                    "service artifacts must belong to a workspace or canonical cache"
                ) from error
            uri = resolved.relative_to(PROJECT_ROOT).as_posix()
        return {
            "artifact_id": f"{role}:{digest[:16]}",
            "media_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
            "uri": uri,
            "sha256": digest,
            "schema_id": _json_schema_id(path),
            "producer": SERVICE_PRODUCER,
            "input_refs": [],
        }

    def _semantic_run_id(self, request: dict[str, Any]) -> str:
        operation = request["operation"]
        operation_input = request["input"]
        output_keys = {"run_directory", "out_directory"}
        closure: dict[str, Any] = {
            "operation": operation,
            "semantic_environment": {
                "runtime_version": __version__,
                "service_request_contract": sha256_file(
                    SERVICE_CONTRACT_ROOT / "service-request.schema.json"
                ),
                "upstream_lock": sha256_file(CONTRACTS_ROOT / "upstream.lock.json"),
            },
            "inputs": {},
        }
        for key, value in sorted(operation_input.items()):
            if key in output_keys:
                continue
            if operation == "realize" and key == "case_directory":
                closure["inputs"][key] = self._case_closure(
                    request["workspace_id"], value
                )
            elif operation == "report" and key == "realization_run_directory":
                closure["inputs"][key] = self._realization_closure(
                    request["workspace_id"], value
                )
            else:
                closure["inputs"][key] = self._semantic_value(
                    request["workspace_id"], value
                )
        digest = sha256_bytes(canonical_json_bytes(closure))
        return f"semrun:sha256:{digest}"

    def _execution_directory(self, semantic_run_id: str, operation: str) -> Path:
        digest = semantic_run_id.removeprefix("semrun:sha256:")
        path = self.execution_cache / digest[:2] / digest / operation
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def _stage_file(source: Path, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists() or sha256_file(destination) != sha256_file(source):
            shutil.copy2(source, destination)
        return destination

    @staticmethod
    def _mirror(source: Path, destination: Path) -> None:
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copytree(
            source,
            destination,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("inputs"),
        )

    def _semantic_value(self, workspace_id: str, value: Any) -> Any:
        if isinstance(value, str):
            path = self.workspaces.resolve(workspace_id, value)
            if path.is_file():
                return {"sha256": sha256_file(path)}
            if path.is_dir():
                return {
                    "files": [
                        {
                            "path": item.relative_to(path).as_posix(),
                            "sha256": sha256_file(item),
                        }
                        for item in sorted(
                            candidate
                            for candidate in path.rglob("*")
                            if candidate.is_file()
                        )
                        if ".sof-service" not in item.parts
                        and "__pycache__" not in item.parts
                        and item.suffix != ".pyc"
                    ]
                }
            return value
        if isinstance(value, dict):
            return {
                key: self._semantic_value(workspace_id, item)
                for key, item in sorted(value.items())
            }
        if isinstance(value, list):
            return [self._semantic_value(workspace_id, item) for item in value]
        return value

    def _case_closure(self, workspace_id: str, relative_path: str) -> dict[str, Any]:
        case_directory = self.workspaces.resolve(
            workspace_id, relative_path, must_exist=True
        )
        case_path = case_directory / "case.json"
        case = load_json(case_path)
        closure: dict[str, Any] = {"case": sha256_file(case_path)}
        for key in ("source", "adapter", "compiler_profile", "assembly_profile"):
            value = case.get(key)
            if not isinstance(value, str):
                continue
            path = self._declared_case_path(
                workspace_id,
                case_directory,
                value,
                allow_runtime_profile=key in {"compiler_profile", "assembly_profile"},
            )
            closure[key] = sha256_file(path)
        return closure

    def _stage_case(
        self,
        workspace_id: str,
        relative_path: str,
        staging_root: Path,
    ) -> Path:
        case_directory = self.workspaces.resolve(
            workspace_id, relative_path, must_exist=True
        )
        case_path = case_directory / "case.json"
        case = load_json(case_path)
        staged_case = staging_root / "case"
        self._stage_file(case_path, staged_case / "case.json")
        for key in ("source", "adapter", "compiler_profile", "assembly_profile"):
            value = case.get(key)
            if not isinstance(value, str):
                continue
            source = self._declared_case_path(
                workspace_id,
                case_directory,
                value,
                allow_runtime_profile=key in {"compiler_profile", "assembly_profile"},
            )
            destination = (staged_case / value).resolve()
            try:
                destination.relative_to(staging_root.resolve())
            except ValueError as error:
                raise WorkspaceViolation(
                    f"declared case path escapes staged bundle: {value}"
                ) from error
            self._stage_file(source, destination)
        return staged_case

    def _declared_case_path(
        self,
        workspace_id: str,
        case_directory: Path,
        value: str,
        *,
        allow_runtime_profile: bool,
    ) -> Path:
        local = (case_directory / value).resolve()
        if local.is_file():
            self.workspaces.relative(workspace_id, local)
            return local
        if allow_runtime_profile:
            profile = (PROJECT_ROOT / value).resolve()
            try:
                profile.relative_to((PROJECT_ROOT / "profiles").resolve())
            except ValueError as error:
                raise WorkspaceViolation(
                    f"runtime profile fallback escapes profiles/: {value}"
                ) from error
            if profile.is_file():
                return profile
        raise FileNotFoundError(local)

    def _realization_closure(
        self,
        workspace_id: str,
        relative_path: str,
    ) -> dict[str, Any]:
        run_directory = self.workspaces.resolve(
            workspace_id, relative_path, must_exist=True
        )
        receipt = load_json(run_directory / "run-receipt.json")
        digests: dict[str, Any] = {
            "eligibility": receipt["eligibility"],
            "source": receipt["source"]["digest"],
            "realization_candidate": receipt["realization_candidate"]["digest"],
            "evidence": receipt["evidence"]["digest"],
            "adapter": {
                key: receipt["adapter"][key]["digest"]
                for key in ("implementation", "declaration", "inspection")
            },
        }
        if "report_profiles" in receipt:
            digests["report_profiles"] = {
                key: value["digest"]
                for key, value in sorted(receipt["report_profiles"].items())
            }
        return digests

    @staticmethod
    def _error(
        code: str,
        message: str,
        *,
        request_id: str | None = None,
        job_id: str | None = None,
    ) -> ServiceError:
        error = ServiceError(
            code,
            message,
            request_id=request_id,
            job_id=job_id,
        )
        validate_contract(
            error.payload,
            SERVICE_CONTRACT_ROOT / "service-error.schema.json",
            label="service error",
        )
        return error
