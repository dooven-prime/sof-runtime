from __future__ import annotations

import unittest

from sof_runtime.carriers.positive_word_support import (
    SUPPORTED_POLICY,
    compute_positive_word_support,
)
from sof_runtime.contracts import load_json
from sof_runtime.paths import PROJECT_ROOT


class PositiveWordSupportUnitTests(unittest.TestCase):
    def test_cycle4_exact_first_hits(self) -> None:
        source = load_json(PROJECT_ROOT / "examples" / "markov" / "cycle4-lazy.json")
        bundle = compute_positive_word_support(
            source,
            semantic_run_id="semrun:sha256:" + "0" * 64,
            execution_id="exec:unit-cycle4",
            policies=SUPPORTED_POLICY,
            created_at="2026-08-04T00:00:00Z",
        )
        payload = bundle["findings"][0]["payload"]
        self.assertEqual(payload["reachable_pair_count"], 12)
        self.assertEqual(payload["unreachable_pair_count"], 0)
        self.assertEqual(payload["maximum_first_hit_depth"], 3)
        self.assertEqual(bundle["object"]["operator_label"], "P")
        self.assertNotIn("reset_depth", payload)
        self.assertNotIn("mixing_time", payload)


if __name__ == "__main__":
    unittest.main()
