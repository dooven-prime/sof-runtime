from __future__ import annotations

import copy
import tempfile
import unittest

from sof_runtime.contracts import load_json
from sof_runtime.paths import PROJECT_ROOT
from sof_runtime.run_identity import verify_semantic_run_id
from sof_runtime.workflow import build_rank_collapse_request


class RunIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = load_json(
            PROJECT_ROOT / "examples" / "automata" / "cerny4.json"
        )

    def test_concrete_environment_does_not_change_semantic_identity(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
            request = build_rank_collapse_request(
                self.source,
                directory,
                execution_id="exec:environment-layer",
                created_at="2026-08-04T00:00:00Z",
            )
        changed = copy.deepcopy(request)
        changed["runtime_environment"]["operating_system"] = "different-os"
        changed["runtime_environment"]["machine_architecture"] = "different-arch"
        self.assertTrue(verify_semantic_run_id(changed))

    def test_semantic_environment_change_invalidates_identity(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT / "runs") as directory:
            request = build_rank_collapse_request(
                self.source,
                directory,
                execution_id="exec:semantic-environment",
                created_at="2026-08-04T00:00:00Z",
            )
        changed = copy.deepcopy(request)
        changed["semantic_environment"]["feature_flags"] = ["alternate-ordering"]
        self.assertFalse(verify_semantic_run_id(changed))


if __name__ == "__main__":
    unittest.main()
