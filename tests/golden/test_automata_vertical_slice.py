from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sof_runtime.contracts import load_json
from sof_runtime.paths import PROJECT_ROOT
from sof_runtime.workflow import (
    run_rank_collapse,
    validate_promotion_package,
    validate_run_response,
)


class AutomataVerticalSliceTests(unittest.TestCase):
    def test_cerny4_source_to_validated_extension_artifacts(self) -> None:
        source = load_json(PROJECT_ROOT / "examples" / "automata" / "cerny4.json")
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
            response = run_rank_collapse(
                source,
                directory,
                execution_id="exec:golden-cerny4",
                created_at="2026-08-04T00:00:00Z",
            )
            certificate = validate_run_response(Path(directory) / "run-response.json")
            self.assertEqual(response["status"], "SUCCEEDED")
            self.assertEqual(certificate["status"], "PASS")
            self.assertEqual(
                response["artifact_closure"]["artifact_count"],
                len(response["outputs"]),
            )
            self.assertEqual(
                response["artifact_closure"]["validator_certificate_digest"],
                next(
                    item["artifact_ref"]["sha256"]
                    for item in response["outputs"]
                    if item["kind"] == "validation_certificate"
                ),
            )
            refs = {item["kind"]: item["artifact_ref"] for item in response["outputs"]}
            self.assertEqual(certificate["input_digests"]["source"], refs["source"]["sha256"])
            self.assertEqual(
                certificate["input_digests"]["bundle"],
                refs["result_bundle"]["sha256"],
            )
            self.assertNotIn("typed_sof_ir", refs)
            self.assertNotIn("compiler_output", refs)
            self.assertNotIn("promotion_package", refs)
            self.assertEqual(
                certificate["validator_independence"],
                {
                    "implementation_relation": "separate_implementation",
                    "language_relation": "same_language",
                    "runtime_relation": "same_process",
                    "input_source": "canonical_source_artifacts",
                    "producer_cache_used": False,
                },
            )
            promotion_path = Path(directory) / "promotion-package.json"
            promotion = validate_promotion_package(
                promotion_path,
                Path(directory) / "run-response.json",
            )
            self.assertEqual(promotion["promotion_state"], "CANDIDATE")
            self.assertEqual(
                promotion["run_response_artifact_closure_digest"],
                response["artifact_closure"]["artifact_manifest_digest"],
            )
            self.assertGreaterEqual(
                len(promotion["negative_evidence"]["separation_statements"]),
                3,
            )


if __name__ == "__main__":
    unittest.main()
