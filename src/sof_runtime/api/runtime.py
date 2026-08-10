"""Small object-oriented facade over the Level 1-3 runtime workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sof_runtime.action import build_interpretation
from sof_runtime.comparison import build_comparison
from sof_runtime.contracts import load_json
from sof_runtime.workflow_external_adapter import (
    build_external_report,
    run_external_realization,
)

from .models import CandidateAction, Comparison, Interpretation, Realization, Report


class RuntimeAPI:
    """Stable application-facing API; JSON contracts remain the wire format."""

    @staticmethod
    def _realization(result: dict[str, Any]) -> Realization:
        return Realization(
            source_id=result["source_id"],
            eligibility=result["eligibility"],
            candidate_path=Path(result["candidate"]),
            declaration_path=Path(result["declaration"]),
            inspection_path=Path(result["inspection"]),
            evidence_path=Path(result["evidence"]),
            run_receipt_path=Path(result["run_receipt"]),
        )

    def realize(self, case_directory: str | Path, run_directory: str | Path) -> Realization:
        """Validate an expert realization without assuming report eligibility."""
        return self._realization(run_external_realization(case_directory, run_directory))

    def load_realization(self, run_directory: str | Path) -> Realization:
        """Reload a realization handle from its source-addressed run receipt."""
        root = Path(run_directory).resolve()
        receipt = load_json(root / "run-receipt.json")
        from sof_runtime.reporting.assembly_v2 import resolve_artifact_reference

        result = {
            "source_id": load_json(resolve_artifact_reference(receipt["realization_candidate"]))["source_id"],
            "eligibility": receipt["eligibility"],
            "candidate": resolve_artifact_reference(receipt["realization_candidate"]),
            "declaration": resolve_artifact_reference(receipt["adapter"]["declaration"]),
            "inspection": resolve_artifact_reference(receipt["adapter"]["inspection"]),
            "evidence": resolve_artifact_reference(receipt["evidence"]),
            "run_receipt": root / "run-receipt.json",
        }
        return self._realization(result)

    def report(
        self,
        realization: Realization,
        output_directory: str | Path | None = None,
        *,
        compiler_profile_path: str | Path | None = None,
        assembly_profile_path: str | Path | None = None,
    ) -> Report:
        """Compile and assemble a canonical-eligible realization."""
        result = build_external_report(
            realization.run_receipt_path.parent,
            output_directory,
            compiler_profile_path=compiler_profile_path,
            assembly_profile_path=assembly_profile_path,
        )
        report = Report(
            report_id=result["report_id"],
            artifact_path=Path(result["report"]),
            validation_receipt_path=Path(result["validation_receipt"]),
        )
        return report

    def realize_and_report(
        self,
        case_directory: str | Path,
        run_directory: str | Path,
    ) -> tuple[Realization, Report]:
        """Reference convenience wrapper for canonical-compilable cases."""
        realization = self.realize(case_directory, run_directory)
        return realization, self.report(realization)

    def compare(
        self,
        reference: Report,
        target: Report,
        *,
        alignment: str | Path,
        profile: str | Path,
        out_dir: str | Path,
    ) -> Comparison:
        result = build_comparison(
            reference.artifact_path,
            reference.validation_receipt_path,
            target.artifact_path,
            target.validation_receipt_path,
            out_dir,
            alignment_path=alignment,
            profile_path=profile,
        )
        return Comparison(
            audit_id=result["audit_id"],
            artifact_path=Path(result["audit"]),
            validation_receipt_path=Path(result["receipt"]),
        )

    def interpret(
        self,
        comparison: Comparison,
        context_path: str | Path,
        policy_path: str | Path,
        output_directory: str | Path,
    ) -> tuple[Interpretation, tuple[CandidateAction, ...]]:
        result = build_interpretation(
            comparison.artifact_path,
            comparison.validation_receipt_path,
            context_path,
            policy_path,
            output_directory,
        )
        action_path = Path(result["action"])
        action_payload = load_json(action_path)
        interpretation = Interpretation(
            action_record_id=result["action_record_id"],
            artifact_path=action_path,
            validation_receipt_path=Path(result["receipt"]),
        )
        candidates = tuple(
            CandidateAction(
                action_id=item["action_id"],
                disposition=item["disposition"],
                artifact_path=action_path,
                validation_receipt_path=Path(result["receipt"]),
            )
            for item in action_payload["candidate_action_set"]["actions"]
        )
        return interpretation, candidates

    def full_pipeline(
        self,
        reference_case: str | Path,
        target_case: str | Path,
        *,
        alignment: str | Path,
        comparison_profile: str | Path,
        action_context: str | Path,
        policy_profile: str | Path,
        run_dir: str | Path,
    ) -> dict[str, Any]:
        root = Path(run_dir)
        reference_realization, reference_report = self.realize_and_report(
            reference_case, root / "reference"
        )
        target_realization, target_report = self.realize_and_report(
            target_case, root / "target"
        )
        comparison = self.compare(
            reference_report,
            target_report,
            alignment=alignment,
            profile=comparison_profile,
            out_dir=root / "comparison",
        )
        interpretation, candidates = self.interpret(
            comparison, action_context, policy_profile, root / "action"
        )
        return {
            "realizations": (reference_realization, target_realization),
            "reports": (reference_report, target_report),
            "comparison": comparison,
            "interpretation": interpretation,
            "candidates": candidates,
        }
