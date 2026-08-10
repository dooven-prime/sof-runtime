"""Stable runtime API objects backed by source-addressed JSON artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sof_runtime.contracts import load_json


@dataclass(frozen=True)
class Realization:
    source_id: str
    eligibility: str
    candidate_path: Path
    declaration_path: Path
    inspection_path: Path
    evidence_path: Path
    run_receipt_path: Path

    @property
    def candidate(self) -> dict[str, Any]:
        return load_json(self.candidate_path)

    @property
    def canonical_compilable(self) -> bool:
        return self.eligibility == "canonical_compilable"


@dataclass(frozen=True)
class Report:
    report_id: str
    artifact_path: Path
    validation_receipt_path: Path

    @property
    def payload(self) -> dict[str, Any]:
        return load_json(self.artifact_path)


@dataclass(frozen=True)
class Comparison:
    audit_id: str
    artifact_path: Path
    validation_receipt_path: Path

    @property
    def payload(self) -> dict[str, Any]:
        return load_json(self.artifact_path)


@dataclass(frozen=True)
class Interpretation:
    action_record_id: str
    artifact_path: Path
    validation_receipt_path: Path

    @property
    def records(self) -> tuple[dict[str, Any], ...]:
        return tuple(load_json(self.artifact_path)["interpretation_records"])


@dataclass(frozen=True)
class CandidateAction:
    action_id: str
    disposition: str
    artifact_path: Path
    validation_receipt_path: Path

    @property
    def payload(self) -> dict[str, Any]:
        action = load_json(self.artifact_path)
        return next(item for item in action["candidate_action_set"]["actions"] if item["action_id"] == self.action_id)
