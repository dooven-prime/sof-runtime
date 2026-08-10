from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

from sof_runtime.artifacts import sha256_bytes
from sof_runtime.carriers.rank_collapse import PLUGIN_ID, PLUGIN_VERSION
from sof_runtime.contracts import load_json
from sof_runtime.contracts.validation import write_json
from sof_runtime.paths import PROJECT_ROOT
from sof_runtime.plugins import ExternalPluginRunner
from sof_runtime.validation.rank_collapse import validate_rank_collapse
from sof_runtime.workflow import (
    run_rank_collapse,
    validate_promotion_package,
    validate_run_response,
)


SOURCE = {
    "schema_id": "rime.automata.source.v1",
    "source_id": "cerny4",
    "states": ["0", "1", "2", "3"],
    "alphabet": ["a", "b"],
    "transitions": {
        "a": ["1", "2", "3", "0"],
        "b": ["0", "1", "2", "0"],
    },
}


class VerticalSliceFailureTests(unittest.TestCase):
    def test_invalid_source_produces_structured_failure(self) -> None:
        invalid = copy.deepcopy(SOURCE)
        del invalid["transitions"]["b"]
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
            response = run_rank_collapse(
                invalid,
                directory,
                execution_id="exec:invalid-source",
                created_at="2026-08-04T00:00:00Z",
            )
            checked = validate_run_response(Path(directory) / "run-response.json")
            self.assertEqual(response["status"], "FAILED_VALIDATION")
            self.assertEqual(response["failure"]["stage"], "INPUT_VALIDATION")
            self.assertFalse(response["failure"]["validator_ran"])
            self.assertEqual(checked, response)

    def test_plugin_exit_produces_structured_failure_with_stderr_digest(self) -> None:
        with tempfile.TemporaryDirectory() as script_directory:
            script = Path(script_directory) / "fail.py"
            script.write_text(
                "import sys\nsys.stderr.write('deliberate failure')\nraise SystemExit(7)\n",
                encoding="utf-8",
            )
            external = ExternalPluginRunner(
                [sys.executable, str(script)],
                plugin_id=PLUGIN_ID,
                plugin_version=PLUGIN_VERSION,
                carrier_kind="rank_collapse",
                implementation_language="python",
            )
            with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
                response = run_rank_collapse(
                    SOURCE,
                    directory,
                    plugin=external,
                    execution_id="exec:plugin-failure",
                    created_at="2026-08-04T00:00:00Z",
                )
                validate_run_response(Path(directory) / "run-response.json")
                self.assertEqual(response["status"], "FAILED_EXECUTION")
                self.assertEqual(response["failure"]["stage"], "PLUGIN_EXECUTION")
                self.assertEqual(
                    response["failure"]["stderr_sha256"],
                    sha256_bytes(b"deliberate failure"),
                )

    def test_artifact_tampering_is_detected(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
            response = run_rank_collapse(
                SOURCE,
                directory,
                execution_id="exec:tamper",
                created_at="2026-08-04T00:00:00Z",
            )
            bundle_ref = next(
                item["artifact_ref"]
                for item in response["outputs"]
                if item["kind"] == "result_bundle"
            )
            (PROJECT_ROOT / bundle_ref["uri"]).write_bytes(b"{}")
            with self.assertRaisesRegex(ValueError, "artifact verification failed"):
                validate_run_response(Path(directory) / "run-response.json")

    def test_run_response_artifact_closure_tampering_is_detected(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
            response = run_rank_collapse(
                SOURCE,
                directory,
                execution_id="exec:closure-tamper",
                created_at="2026-08-04T00:00:00Z",
            )
            response["artifact_closure"]["artifact_count"] += 1
            write_json(Path(directory) / "run-response.json", response)
            with self.assertRaisesRegex(ValueError, "artifact closure mismatch"):
                validate_run_response(Path(directory) / "run-response.json")

    def test_promotion_rejects_artifact_outside_frozen_closure(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
            response_path = Path(directory) / "run-response.json"
            package_path = Path(directory) / "promotion-package.json"
            response = run_rank_collapse(
                SOURCE,
                directory,
                execution_id="exec:closure-extra",
                created_at="2026-08-04T00:00:00Z",
            )
            promotion = load_json(package_path)
            supplemental = copy.deepcopy(response["outputs"][0]["artifact_ref"])
            supplemental["artifact_id"] = "artifact.supplemental-evidence"
            promotion["artifact_refs"].append(supplemental)
            write_json(package_path, promotion)
            with self.assertRaisesRegex(ValueError, "artifact set differs"):
                validate_promotion_package(package_path, response_path)

    def test_validator_version_mismatch_is_detected(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
            response = run_rank_collapse(
                SOURCE,
                directory,
                execution_id="exec:validator-version",
                created_at="2026-08-04T00:00:00Z",
            )
            response["validator"]["validator_version"] = "9.9.9"
            write_json(Path(directory) / "run-response.json", response)
            with self.assertRaisesRegex(ValueError, "validator identity mismatch"):
                validate_run_response(Path(directory) / "run-response.json")

    def test_changed_source_fails_old_bundle_validation(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
            response = run_rank_collapse(
                SOURCE,
                directory,
                execution_id="exec:source-change",
                created_at="2026-08-04T00:00:00Z",
            )
            outputs = {item["kind"]: item for item in response["outputs"]}
            bundle = load_json(PROJECT_ROOT / outputs["result_bundle"]["artifact_ref"]["uri"])
            changed = copy.deepcopy(SOURCE)
            changed["transitions"]["b"] = ["0", "1", "1", "0"]
            certificate = validate_rank_collapse(changed, bundle)
            self.assertEqual(certificate["status"], "FAIL")
            self.assertIn("source digest mismatch", certificate["recomputed"]["errors"])

    def test_policy_change_changes_semantic_identity_and_is_structured(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as exact_dir:
            exact = run_rank_collapse(
                SOURCE,
                exact_dir,
                execution_id="exec:policy-exact",
                created_at="2026-08-04T00:00:00Z",
            )
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as cutoff_dir:
            cutoff = run_rank_collapse(
                SOURCE,
                cutoff_dir,
                policies={"rank_collapse": {"mode": "cutoff", "max_depth": 8}},
                execution_id="exec:policy-cutoff",
                created_at="2026-08-04T00:00:00Z",
            )
            validate_run_response(Path(cutoff_dir) / "run-response.json")
        self.assertNotEqual(exact["semantic_run_id"], cutoff["semantic_run_id"])
        self.assertEqual(cutoff["status"], "UNSUPPORTED")
        self.assertEqual(cutoff["failure"]["stage"], "POLICY_ADMISSION")

    def test_repeated_input_reuses_semantic_identity_not_execution_identity(self) -> None:
        responses = []
        bundles = []
        for suffix in ("a", "b"):
            with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
                response = run_rank_collapse(
                    SOURCE,
                    directory,
                    execution_id=f"exec:repeat-{suffix}",
                    created_at="2026-08-04T00:00:00Z",
                )
                outputs = {item["kind"]: item for item in response["outputs"]}
                bundle = load_json(
                    PROJECT_ROOT / outputs["result_bundle"]["artifact_ref"]["uri"]
                )
                responses.append(response)
                bundles.append(bundle)
        self.assertEqual(responses[0]["semantic_run_id"], responses[1]["semantic_run_id"])
        self.assertNotEqual(responses[0]["execution_id"], responses[1]["execution_id"])
        self.assertEqual(bundles[0]["image_layers"], bundles[1]["image_layers"])
        self.assertEqual(
            [item["payload"] for item in bundles[0]["findings"]],
            [item["payload"] for item in bundles[1]["findings"]],
        )


if __name__ == "__main__":
    unittest.main()
