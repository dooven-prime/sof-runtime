"""Small file-backed job ledger for transport-neutral service execution."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from sof_runtime.contracts.validation import write_json
from sof_runtime.paths import SERVICE_CONTRACT_ROOT
from sof_runtime.contracts import load_json, validate_contract

from .workspace import WorkspaceManager


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class JobStore:
    def __init__(self, workspaces: WorkspaceManager):
        self.workspaces = workspaces

    def create(self, request: dict[str, Any]) -> dict[str, Any]:
        job = {
            "contract_id": "sof-runtime.service-job.v1",
            "job_id": f"job:{uuid4().hex}",
            "request_id": request["request_id"],
            "workspace_id": request["workspace_id"],
            "operation": request["operation"],
            "state": "queued",
            "submitted_at": _now(),
        }
        self._write(job)
        return deepcopy(job)

    def start(self, job: dict[str, Any]) -> dict[str, Any]:
        job = deepcopy(job)
        job.update(state="running", started_at=_now())
        self._write(job)
        return job

    def succeed(self, job: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
        job = deepcopy(job)
        job.update(state="succeeded", completed_at=_now(), response=response)
        self._write(job)
        return job

    def fail(self, job: dict[str, Any], error: dict[str, Any]) -> dict[str, Any]:
        job = deepcopy(job)
        job.update(state="failed", completed_at=_now(), error=error)
        self._write(job)
        return job

    def get(self, workspace_id: str, job_id: str) -> dict[str, Any]:
        if not job_id.startswith("job:"):
            raise FileNotFoundError(job_id)
        path = self._path(workspace_id, job_id)
        if not path.is_file():
            raise FileNotFoundError(path)
        job = load_json(path)
        validate_contract(job, SERVICE_CONTRACT_ROOT / "job.schema.json", label="job")
        return job

    def _path(self, workspace_id: str, job_id: str) -> Path:
        return self.workspaces.resolve(
            workspace_id,
            Path(".sof-service") / "jobs" / f"{job_id.removeprefix('job:')}.json",
        )

    def _write(self, job: dict[str, Any]) -> None:
        validate_contract(job, SERVICE_CONTRACT_ROOT / "job.schema.json", label="job")
        write_json(self._path(job["workspace_id"], job["job_id"]), job)
