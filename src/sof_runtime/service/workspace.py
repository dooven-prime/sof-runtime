"""Workspace confinement for transport-facing runtime operations."""

from __future__ import annotations

import re
from pathlib import Path

from sof_runtime.paths import PROJECT_ROOT


_WORKSPACE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class WorkspaceViolation(ValueError):
    pass


class WorkspaceManager:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        try:
            self.root.relative_to(PROJECT_ROOT)
        except ValueError as error:
            raise WorkspaceViolation(
                "service workspace root must remain inside SOF_RUNTIME_WORKSPACE"
            ) from error
        self.root.mkdir(parents=True, exist_ok=True)

    def workspace(self, workspace_id: str, *, create: bool = True) -> Path:
        if not _WORKSPACE_ID.fullmatch(workspace_id):
            raise WorkspaceViolation(f"invalid workspace_id: {workspace_id!r}")
        workspace = (self.root / workspace_id).resolve()
        self._assert_within(workspace, self.root)
        if create:
            workspace.mkdir(parents=True, exist_ok=True)
        return workspace

    def resolve(
        self,
        workspace_id: str,
        relative_path: str | Path,
        *,
        must_exist: bool = False,
    ) -> Path:
        path = Path(relative_path)
        if path.is_absolute():
            raise WorkspaceViolation("service paths must be workspace-relative")
        workspace = self.workspace(workspace_id)
        resolved = (workspace / path).resolve()
        self._assert_within(resolved, workspace)
        if must_exist and not resolved.exists():
            raise FileNotFoundError(resolved)
        return resolved

    def relative(self, workspace_id: str, path: str | Path) -> str:
        workspace = self.workspace(workspace_id, create=False)
        resolved = Path(path).resolve()
        self._assert_within(resolved, workspace)
        return resolved.relative_to(workspace).as_posix()

    @staticmethod
    def _assert_within(path: Path, parent: Path) -> None:
        try:
            path.relative_to(parent)
        except ValueError as error:
            raise WorkspaceViolation(f"path escapes workspace: {path}") from error
