from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2] / "evaluations" / "adapter-boundary-lab-v1"


def _load_runner():
    spec = importlib.util.spec_from_file_location("adapter_boundary_lab", ROOT / "run_lab.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AdapterBoundaryLabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = _load_runner()
        cls.fixtures = cls.runner.json.loads((ROOT / "fixtures.json").read_text(encoding="utf-8"))

    def test_all_boundary_fixtures_pass(self) -> None:
        summary = self.runner.run_lab(self.fixtures)
        self.assertEqual(summary["status"], "PASS")
        self.assertEqual(summary["fixture_count"], 5)
        self.assertEqual({item["status"] for item in summary["results"]}, {"PASS"})
        self.assertEqual(len(summary["input_closure"]["fixtures_sha256"]), 64)
        self.assertEqual(len(summary["input_closure"]["runner_sha256"]), 64)

    def test_each_fixture_declares_claim_and_nonclaims(self) -> None:
        for fixture in self.fixtures["fixtures"]:
            self.assertTrue(fixture["strongest_claim"])
            self.assertIn(fixture["strongest_claim_level"], {
                "Theorem",
                "Computational Certificate",
                "Computational Observation",
                "Research Program",
            })
            self.assertGreater(len(fixture["known_nonclaims"]), 0)

    def test_boundary_specific_observations(self) -> None:
        results = {
            item["fixture_id"]: item
            for item in self.runner.run_lab(self.fixtures)["results"]
        }
        self.assertEqual(results["signed-cancellation"]["observations"]["matrix_square_entry_0_2"], "0")
        self.assertEqual(results["multi-letter-word"]["observations"]["selected_word_entry_0_2"], "0")
        self.assertEqual(results["cutoff-unreached"]["observations"]["pair_values"]["0->3"], "UNREACHED_AT_CUTOFF")
        self.assertEqual(
            [row["support_count"] for row in results["threshold-sweep"]["observations"]["rows"]],
            [2, 1, 0],
        )

    def test_committed_summary_matches_recomputation(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "run_lab.py"), "--check"],
            cwd=ROOT.parents[1],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
