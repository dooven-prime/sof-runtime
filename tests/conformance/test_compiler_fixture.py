from __future__ import annotations

import unittest

from sof_runtime.compiler import compile_documents
from sof_runtime.contracts import load_json
from sof_runtime.paths import PROJECT_ROOT


FIXTURES = PROJECT_ROOT / "tests" / "conformance" / "fixtures" / "upstream-v1.0"


class CompilerConformanceTests(unittest.TestCase):
    def test_reference_compiler_reproduces_upstream_fixture(self) -> None:
        actual = compile_documents(
            load_json(FIXTURES / "strict-associative-capabilities-v1.0.json"),
            load_json(FIXTURES / "strict-associative-ir-v1.0.json"),
            load_json(FIXTURES / "basic-associative-closure-profile-v1.0.json"),
            verify_artifacts=False,
        )
        expected = load_json(
            FIXTURES / "strict-associative-compiler-output-v1.0.json"
        )
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
