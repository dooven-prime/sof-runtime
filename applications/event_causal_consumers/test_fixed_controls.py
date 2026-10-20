"""Contract tests for the unpromoted, fixed-domain Q2 design spike."""

import os
from pathlib import Path
import unittest

from fixed_controls import (
    LimitReached, frozen_models, generated_domain, kernel_check, operator_check,
    run, saturate, semantic_check, track_report, TRACK,
)


class FixedControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = os.environ.get("RIME_LITE_UPSTREAM")
        snapshot = os.environ.get("RIME_PAPER39_SNAPSHOT")
        if not root and not snapshot:
            raise unittest.SkipTest("Set RIME_LITE_UPSTREAM or RIME_PAPER39_SNAPSHOT")
        cls.context = frozen_models(None if snapshot else Path(root), source_dir=snapshot)
        cls.models = cls.context.__enter__()
        cls.addClassCleanup(cls.context.__exit__, None, None, None)

    def test_fixed_positive_negative_and_operator_controls(self):
        result = run(self.models)
        self.assertEqual(result["status"], "PASS_FIXED_CONTROLS")
        self.assertEqual(len(result["cases"]), 9)
        self.assertFalse(result["full_grammar_interpreter"])
        self.assertFalse(result["canonical_compiler_admission"])

    def test_state_limit_is_not_a_mathematical_failure(self):
        env = self.models["contract"].Environment((0, 2, 0), (0, 1, 2), (0, 1, 2))
        log = self.models["log_consumer"]
        with self.assertRaises(LimitReached):
            saturate(log.initial(env), lambda x, a: log.step(env, x, a), 1)

    def test_exact_gamma_fibers_and_invariant_kernel(self):
        env = self.models["contract"].Environment((0, 0, 1, 2), (0, 1, 2, 3), (0, 1, 2, 3))
        domain = generated_domain(self.models, env, frozenset({0, 1}))
        result = kernel_check(self.models, domain, lambda s: s, track_report, TRACK)
        self.assertEqual(len(domain.forest_states), 84)
        self.assertEqual(len(domain.summaries), 72)
        self.assertEqual(result["fiber_size_distribution"], {1: 60, 2: 12})
        self.assertEqual(result["kernel_dimension"], 12)
        self.assertEqual(result["status"], "PASS_EXACT")

    def test_empty_registered_domain_is_not_source_supply(self):
        env = self.models["contract"].Environment((0, 0), (0, 1), (0, 1))
        domain = generated_domain(self.models, env, frozenset({0}))
        self.assertFalse(domain.summaries)
        self.assertFalse(domain.forest_states)
        for checker in (semantic_check, operator_check, kernel_check):
            decision = checker(self.models, domain, lambda s: s, lambda s: s, TRACK)
            self.assertEqual(decision["status"], "EMPTY_REGISTERED_DOMAIN")

    def test_forward_intertwining_does_not_imply_adjoint_intertwining(self):
        fine_columns = (0, 0)
        # L maps either basis vector to the only coarse basis vector.
        self.assertEqual(tuple(1 for _ in fine_columns), (1, 1))
        fine_adjoint_then_l = tuple(fine_columns.count(i) for i in range(2))
        coarse_adjoint_after_l = (1, 1)
        self.assertEqual(fine_adjoint_then_l, (2, 0))
        self.assertNotEqual(fine_adjoint_then_l, coarse_adjoint_after_l)

    def test_invalid_limit_is_an_input_error(self):
        with self.assertRaises(ValueError):
            saturate(0, lambda x, a: x, 0)


if __name__ == "__main__":
    unittest.main()
