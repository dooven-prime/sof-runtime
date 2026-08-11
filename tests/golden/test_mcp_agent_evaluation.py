from __future__ import annotations

import subprocess
import sys
import unittest

from sof_runtime.paths import PROJECT_ROOT


class McpAgentEvaluationTests(unittest.TestCase):
    def test_recorded_black_box_summary_is_structurally_consistent(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "tools/validate_mcp_agent_evaluation.py",
                "evaluations/mcp-agent-blackbox-v1",
            ],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
