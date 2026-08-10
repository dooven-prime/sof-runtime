from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from sof_runtime.adapters.expert import load_expert_adapter
from sof_runtime.contracts import ContractError, load_json
from sof_runtime.explain import explain_run
from sof_runtime.api import RuntimeAPI
from sof_runtime.action import validate_action_validation_receipt
from sof_runtime.comparison import validate_audit_validation_receipt
from sof_runtime.paths import PROJECT_ROOT
from sof_runtime.workflow_external_adapter import run_external_adapter


CASE = PROJECT_ROOT / "examples" / "external-adapter-finite-state"


class ExternalAdapterWorkflowTests(unittest.TestCase):
    def test_external_expert_source_reaches_valid_sofrs(self) -> None:
        adapter = load_expert_adapter(CASE / "adapter.py")
        candidate = adapter.realize(
            load_json(CASE / "source" / "input.json"),
            {
                "workflow_version": "1.0",
                "case_id": "finite-state.transition.v1",
                "source_id": "finite-state.transition.example",
                "adapter_id": "example.finite-state-adapter",
                "adapter_version": "1.0",
            },
        )
        self.assertNotIn("manifest", candidate)
        self.assertNotIn("ir", candidate)
        self.assertIn("direct_support", candidate)

        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
            result = run_external_adapter(CASE, directory)
            self.assertEqual(result["status"], "PASS")
            report = load_json(result["report"])
            receipt = load_json(result["validation_receipt"])
            run_receipt = load_json(result["run_receipt"])
            self.assertEqual(report["record_kind"], "strict_sof")
            self.assertEqual(receipt["status"], "PASS")
            self.assertEqual(run_receipt["status"], "PASS")
            self.assertEqual(report["source_mapping"]["status"], "adapter-derived")
            self.assertEqual(
                report["claims"][0]["claim_status"],
                "Computational Certificate",
            )
            self.assertTrue(report["degradation_items"])

    def test_runtime_api_exposes_level_one_to_three_object_chain(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
            result = RuntimeAPI().full_pipeline(
                CASE / "reference",
                CASE / "target",
                alignment=CASE / "comparison" / "alignment.json",
                comparison_profile=PROJECT_ROOT / "profiles" / "comparison" / "external-adapter-identity-v2.0.json",
                action_context=CASE / "action" / "context.json",
                policy_profile=CASE / "action" / "policy.json",
                run_dir=directory,
            )

            realizations = result["realizations"]
            reports = result["reports"]
            comparison = result["comparison"]
            interpretation = result["interpretation"]
            candidates = result["candidates"]

            self.assertEqual(len(realizations), 2)
            self.assertTrue(all(item.candidate_path.is_file() for item in realizations))
            self.assertTrue(all(item.source_id for item in realizations))
            self.assertEqual(len(reports), 2)
            self.assertTrue(all(item.payload["record_kind"] == "strict_sof" for item in reports))
            self.assertEqual(comparison.payload["audit_id"], comparison.audit_id)
            self.assertEqual(
                validate_audit_validation_receipt(
                    comparison.validation_receipt_path,
                    repository_root=PROJECT_ROOT,
                )["status"],
                "PASS",
            )
            self.assertEqual(
                comparison.payload["audit_profile"]["profile_id"],
                "sof-runtime.external-adapter.identity.v2",
            )
            self.assertTrue(
                comparison.payload["alignment"]["sector_alignment"]["alignment_id"].startswith(
                    "example.finite-state.identity."
                )
            )
            artifact_ids = {
                item["id"] for item in comparison.payload["source_artifacts"]
            }
            self.assertIn("artifact.audit-profile", artifact_ids)
            self.assertIn("artifact.coordinate-semantics-registry", artifact_ids)
            self.assertEqual(interpretation.records[0]["audit_coordinate_refs"][0]["coordinate_id"], "operator.support.summary")
            self.assertEqual(
                {item.disposition for item in candidates},
                {"Investigate", "RequestEvidence"},
            )
            self.assertTrue(all(item.payload["action_id"] == item.action_id for item in candidates))
            self.assertEqual(
                validate_action_validation_receipt(
                    interpretation.validation_receipt_path,
                    repository_root=PROJECT_ROOT,
                )["status"],
                "PASS",
            )
            explanation = explain_run(directory)
            self.assertEqual(explanation["workflow"], "full_pipeline")
            self.assertEqual(len(explanation["realizations"]), 2)
            self.assertEqual(explanation["comparison"]["validation"]["status"], "PASS")
            self.assertEqual(len(explanation["interpretation"]["candidate_actions"]), 2)

    def test_level_one_stops_for_extension_only_realization(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
            case = Path(directory) / "extension-case"
            case.mkdir()
            (case / "source.json").write_text(
                json.dumps({"source_id": "new.domain.example", "objects": ["x"]}),
                encoding="utf-8",
            )
            (case / "case.json").write_text(
                json.dumps({
                    "case_id": "new.domain.case.v1",
                    "source": "source.json",
                    "adapter": "adapter.py",
                }),
                encoding="utf-8",
            )
            (case / "adapter.py").write_text(
                """
from sof_runtime.sdk import ExpertAdapter

class Adapter:
    def describe(self):
        return {
            "declaration_version": "1.0",
            "adapter_id": "new.domain.adapter",
            "adapter_version": "1.0",
            "domain_id": "new-domain",
            "native_objects": ["domain object"],
            "supported_carriers": ["new-domain-carrier"],
            "supported_observables": ["new-domain-observable"],
            "sectorization_origin": "domain-defined",
            "capabilities": ["domain realization"],
            "unsupported_capabilities": ["canonical SOF carrier"],
            "parameterization": {"kind": "finite fixture"},
            "normalization_threshold_requirements": {"kind": "domain-defined"},
            "evidence_requirements": ["source snapshot"],
        }

    def inspect_source(self, source):
        return {"status": "PASS", "checks": ["source shape"]}

    def realize(self, source, request):
        return {
            "candidate_version": "1.0",
            "candidate_kind": "extension_only",
            "source_id": request["source_id"],
            "extension_contract": {
                "contract_id": "new-domain.realization",
                "contract_version": "1.0",
            },
            "payload": {"objects": source["objects"]},
            "negative_boundary": ["No canonical SOF carrier has been promoted."],
        }

    def evidence(self):
        return {"status": "PASS", "scope": "source-shape control"}

ADAPTER = Adapter()
""",
                encoding="utf-8",
            )

            run_dir = Path(directory) / "run"
            runtime = RuntimeAPI()
            realization = runtime.realize(case, run_dir)
            self.assertEqual(realization.eligibility, "extension_only")
            self.assertFalse(realization.canonical_compilable)
            self.assertTrue(realization.candidate_path.is_file())
            self.assertFalse((run_dir / "compiler").exists())
            explanation = explain_run(run_dir)
            self.assertEqual(explanation["realizations"][0]["eligibility"], "extension_only")
            self.assertNotIn("report", explanation["realizations"][0])
            with self.assertRaises(ContractError):
                runtime.report(realization)


if __name__ == "__main__":
    unittest.main()
