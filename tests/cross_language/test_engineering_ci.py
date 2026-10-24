import unittest
from pathlib import Path
import tempfile
from unittest.mock import patch
from tools.run_engineering_ci import outcome, guard, fixture_temp_root


class ReportingTests(unittest.TestCase):
    def test_skip_does_not_become_pass(self):
        class Skipped(unittest.TestCase):
            @unittest.skip("unsupported platform")
            def test_not_run(self): pass
        r = unittest.TestResult(); Skipped("test_not_run").run(r)
        self.assertEqual(outcome(r), "UNRESOLVED_COVERAGE")

    def test_empty_selection_does_not_become_pass(self):
        self.assertEqual(outcome(unittest.TestResult()), "UNRESOLVED_COVERAGE")

    def test_existing_protected_baseline_is_not_a_test_receipt(self):
        r = guard()
        self.assertEqual(r["status"], "MATCHED_PROTECTED_BYTES")
        self.assertFalse(r["historical_tests_reexecuted_by_this_check"])

    def test_stable_builder_does_not_implicitly_build_prototypes(self):
        from tools import build_rust_plugins as builder
        for args, expected in ((["builder"], 1), (["builder", "--engineering"], 3)):
            with self.subTest(args=args), patch("sys.argv", args), patch.object(builder, "find_cargo", return_value=Path("cargo")), patch.object(builder.subprocess, "run") as run:
                self.assertEqual(builder.main(), 0)
                self.assertEqual(run.call_count, expected)
                self.assertIn(str(builder.MANIFEST), run.call_args_list[0].args[0])


    def test_fixture_temp_root_is_scoped_and_restored_even_on_failure(self):
        with tempfile.TemporaryDirectory() as parent:
            previous = tempfile.tempdir
            with self.assertRaisesRegex(RuntimeError, "test interruption"):
                with fixture_temp_root(Path(parent)) as root:
                    self.assertEqual(root.parent, Path(parent).resolve())
                    self.assertEqual(Path(tempfile.gettempdir()), root)
                    with tempfile.TemporaryDirectory() as fixture:
                        self.assertEqual(Path(fixture).parent, root)
                    raise RuntimeError("test interruption")
            self.assertEqual(tempfile.tempdir, previous)
            self.assertFalse(root.exists())


if __name__ == "__main__": unittest.main()
