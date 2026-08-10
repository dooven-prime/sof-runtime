from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

from sof_runtime.artifacts import canonical_json_bytes, sha256_bytes
from sof_runtime.contracts import ContractError, load_json


class CanonicalJsonTests(unittest.TestCase):
    def test_key_order_whitespace_unicode_and_no_newline_are_fixed(self) -> None:
        payload = {"z": [3, True, None], "a": "caf\u00e9"}
        encoded = canonical_json_bytes(payload)
        self.assertEqual(encoded, b'{"a":"caf\xc3\xa9","z":[3,true,null]}')
        self.assertFalse(encoded.endswith(b"\n"))
        self.assertEqual(
            sha256_bytes(encoded),
            "9ebb0a5694eab1694b3f7a388c44f3e6f3d20212ad3b3c6c999ca380814a55db",
        )

    def test_binary_float_is_rejected(self) -> None:
        for value in (0.0, -0.0, float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                canonical_json_bytes({"value": value})

    def test_non_nfc_string_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            canonical_json_bytes({"value": "e\u0301"})

    def test_integer_range_is_fixed(self) -> None:
        canonical_json_bytes({"minimum": -(2**63), "maximum": 2**63 - 1})
        with self.assertRaises(ValueError):
            canonical_json_bytes({"too_large": 2**63})

    def test_parser_rejects_duplicate_keys_and_nonstandard_numbers(self) -> None:
        for content in (
            '{"a":1,"a":2}',
            '{"value":NaN}',
            '{"value":Infinity}',
            '{"value":-0}',
        ):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "payload.json"
                path.write_text(content, encoding="utf-8")
                with self.subTest(content=content), self.assertRaises(ContractError):
                    load_json(path)


if __name__ == "__main__":
    unittest.main()
