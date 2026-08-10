from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .digest import canonical_json_bytes, sha256_bytes, sha256_file


class ArtifactStore:
    """Content-addressed file store rooted inside one declared run directory."""

    def __init__(self, run_directory: str | Path, repository_root: str | Path):
        self.run_directory = Path(run_directory).resolve()
        self.repository_root = Path(repository_root).resolve()
        self.root = self.run_directory / "artifacts" / "sha256"
        self.root.mkdir(parents=True, exist_ok=True)

    def _relative_uri(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.repository_root).as_posix()
        except ValueError as error:
            raise ValueError("artifact path must remain inside the repository") from error

    def put_bytes(
        self,
        data: bytes,
        *,
        artifact_id: str,
        media_type: str,
        role: str,
        schema_version: str | None,
        suffix: str = ".bin",
    ) -> dict[str, Any]:
        digest = sha256_bytes(data)
        path = self.root / digest[:2] / f"{digest}{suffix}"
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and sha256_file(path) != digest:
            raise ValueError(f"artifact collision at {path}")
        if not path.exists():
            path.write_bytes(data)
        return {
            "id": artifact_id,
            "uri": self._relative_uri(path),
            "digest": {"algorithm": "sha256", "value": digest},
            "media_type": media_type,
            "schema_version": schema_version,
            "role": role,
        }

    def put_json(
        self,
        payload: Any,
        *,
        artifact_id: str,
        role: str,
        schema_version: str | None,
    ) -> dict[str, Any]:
        data = canonical_json_bytes(payload)
        return self.put_bytes(
            data,
            artifact_id=artifact_id,
            media_type="application/json",
            role=role,
            schema_version=schema_version,
            suffix=".json",
        )

    def load_json(self, artifact: dict[str, Any]) -> Any:
        path = self.repository_root / artifact["uri"]
        self.verify(artifact)
        return json.loads(path.read_text(encoding="utf-8"))

    def verify(self, artifact: dict[str, Any]) -> None:
        if artifact["digest"]["algorithm"] != "sha256":
            raise ValueError("the reference artifact store supports sha256 only")
        path = (self.repository_root / artifact["uri"]).resolve()
        try:
            path.relative_to(self.root)
        except ValueError as error:
            raise ValueError("artifact URI escapes the content-addressed store") from error
        if not path.is_file():
            raise ValueError(f"artifact is missing: {path}")
        if sha256_file(path) != artifact["digest"]["value"]:
            raise ValueError(f"artifact digest mismatch: {path}")
