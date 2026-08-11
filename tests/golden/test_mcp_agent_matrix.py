from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from sof_runtime.paths import PROJECT_ROOT


class McpAgentMatrixTests(unittest.TestCase):
    def test_current_service_implementation_closure_is_pinned(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "tools/check_service_implementation_closure.py",
                "evaluations/mcp-agent-matrix-v1/service-closure.current.json",
            ],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_recorded_matrix_matches_digest_bound_summary(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "tools/score_mcp_agent_matrix.py",
                "evaluations/mcp-agent-matrix-v1",
                "--check-summary",
            ],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_complete_synthetic_matrix_computes_macro_rates(self) -> None:
        source = PROJECT_ROOT / "evaluations" / "mcp-agent-matrix-v1"
        with tempfile.TemporaryDirectory() as directory:
            matrix = Path(directory) / "matrix"
            shutil.copytree(source, matrix)
            rubric = json.loads(
                (matrix / "scoring-rubric.json").read_text(encoding="utf-8")
            )
            config_path = matrix / "matrix-config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["status"] = "complete"
            implementation_digest = config["server_closure"][
                "implementation_closure"
            ]["sha256"]
            config_path.write_text(
                json.dumps(config, indent=2) + "\n",
                encoding="utf-8",
            )
            for agent_id in ("agent-a", "agent-b", "agent-c"):
                path = matrix / "runs" / f"{agent_id}.json"
                result = json.loads(path.read_text(encoding="utf-8"))
                result["status"] = "complete"
                result["agent_identity"] = {
                    "provider": "synthetic",
                    "model": agent_id,
                    "model_version": "fixture",
                    "model_version_status": "reported",
                    "harness": "unit-test",
                    "run_timestamp": "2026-08-11T00:00:00Z",
                }
                result["server_closure"][
                    "implementation_closure_sha256"
                ] = implementation_digest
                result["tasks"]["normal_workflow"].update(
                    status="complete",
                    completed_milestones=rubric["normal_workflow_milestones"],
                )
                result["tasks"]["epistemic_hostile"]["status"] = "complete"
                result["tasks"]["operational_hostile"]["status"] = "complete"
                result["metrics"] = {
                    "tool_completion_rate": 1.0,
                    "observed_boundary_category_rate": 0.0,
                    "unsupported_inference_rate": 0.0,
                }
                path.write_text(
                    json.dumps(result, indent=2) + "\n",
                    encoding="utf-8",
                )

            completed = subprocess.run(
                [
                    sys.executable,
                    "tools/score_mcp_agent_matrix.py",
                    str(matrix),
                ],
                cwd=PROJECT_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                completed.returncode,
                0,
                completed.stdout + completed.stderr,
            )
            summary = json.loads(completed.stdout)
            self.assertEqual(summary["status"], "complete")
            self.assertEqual(summary["completed_agent_count"], 3)
            self.assertEqual(summary["aggregate"]["tool_completion_rate"], 1.0)
            self.assertEqual(
                summary["aggregate"]["observed_boundary_category_rate"], 0.0
            )
            self.assertEqual(summary["aggregate"]["unsupported_inference_rate"], 0.0)
            self.assertEqual(
                summary["reviewed_boundary_violations"],
                {
                    "violating_runs": 0,
                    "reviewed_runs": 3,
                    "declared_runs": 3,
                    "rate": 0.0,
                },
            )
            self.assertEqual(summary["declared_model_count"], 3)
            self.assertTrue(summary["cross_model_claim_authorized"])

    def test_modified_response_evidence_is_rejected(self) -> None:
        source = PROJECT_ROOT / "evaluations" / "mcp-agent-matrix-v1"
        with tempfile.TemporaryDirectory() as directory:
            matrix = Path(directory) / "matrix"
            shutil.copytree(source, matrix)
            response = matrix / "runs" / "agent-a-operational.md"
            response.write_text(
                response.read_text(encoding="utf-8") + "\nmodified\n",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    "tools/score_mcp_agent_matrix.py",
                    str(matrix),
                ],
                cwd=PROJECT_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("response digest mismatch", completed.stdout)


if __name__ == "__main__":
    unittest.main()
