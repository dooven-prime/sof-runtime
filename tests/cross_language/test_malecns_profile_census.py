from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from applications.malecns_profile_census.prepare_input import fixture_data
from applications.malecns_profile_census.protocol import canonical_bytes, write_packet
from applications.malecns_profile_census.oracle import run as run_python


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CRATE = PROJECT_ROOT / "plugins/rust/malecns-profile-census"
FIXTURE = PROJECT_ROOT / "examples/malecns_profile_census/tiny-fixture.json"


def cargo_path() -> str | None:
    configured = os.environ.get("CARGO")
    return configured or shutil.which("cargo")


class MaleCNSProfileCensusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cargo = cargo_path()
        if cargo is None:
            raise unittest.SkipTest("Cargo is required for the Rust profile-census cross-check")
        subprocess.run(
            [cargo, "build", "--release", "--locked", "--manifest-path", str(CRATE / "Cargo.toml")],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        suffix = ".exe" if os.name == "nt" else ""
        cls.binary = CRATE / "target/release" / f"malecns-profile-census{suffix}"

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.packet = Path(self.temp.name) / "tiny.input.bin"
        header, records = fixture_data(FIXTURE)
        write_packet(self.packet, header, records)

    def rust_result(self, packet: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(self.binary), str(packet or self.packet)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def test_exact_counts_signatures_and_coordinate_statistics_match(self) -> None:
        expected = run_python(self.packet)
        rust = self.rust_result()
        self.assertEqual(rust.returncode, 0, rust.stderr)
        actual = json.loads(rust.stdout)
        self.assertEqual(canonical_bytes(actual), canonical_bytes(expected))
        self.assertEqual((expected["eligible_sources"], expected["profile_classes"]), (11, 8))
        left, middle = expected["sectors"][1:3]
        self.assertEqual((left["eligible_sources"], left["profile_classes"], left["largest_class_sources"]), (5, 3, 2))
        self.assertEqual((middle["eligible_sources"], middle["profile_classes"], middle["largest_class_sources"]), (3, 2, 2))
        self.assertEqual(left["minimum_separating_coordinate_sets"], [["L"]])
        self.assertEqual(middle["minimum_separating_coordinate_sets"], [["<missing>"], ["L"]])
        self.assertEqual(expected["minimum_global_separating_coordinate_sets"], [
            ["L", "M"], ["L", "R"]
        ])
        right = expected["sectors"][3]
        self.assertEqual(right["minimum_separating_coordinate_sets"], [
            ["<missing>", "M"], ["<missing>", "R"], ["L", "M"], ["L", "R"]
        ])
        self.assertEqual([sum(row["coordinate_separated_class_pairs"][j] for row in expected["sectors"]) for j in range(4)], [3, 6, 4, 4])

    def test_negative_sources_share_the_exact_zero_positive_profile(self) -> None:
        result = run_python(self.packet)
        left = result["sectors"][1]
        self.assertEqual(left["profile_classes"], 3)
        self.assertEqual(left["largest_class_sources"], 2)

    def test_rust_rejects_truncation_and_trailing_bytes(self) -> None:
        truncated = Path(self.temp.name) / "truncated.bin"
        raw = self.packet.read_bytes()
        truncated.write_bytes(raw[:-1])
        result = self.rust_result(truncated)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

        trailing = Path(self.temp.name) / "trailing.bin"
        trailing.write_bytes(raw + b"x")
        result = self.rust_result(trailing)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_rust_rejects_row_mass_overflow_without_a_partial_result(self) -> None:
        overflowing = Path(self.temp.name) / "overflowing.bin"
        raw = bytearray(self.packet.read_bytes())
        header_length = int.from_bytes(raw[8:12], "little")
        first_edge_weight = 12 + header_length + 15 + 2
        raw[first_edge_weight:first_edge_weight + 8] = ((1 << 63) - 1).to_bytes(8, "little")
        overflowing.write_bytes(raw)
        with self.assertRaises(OverflowError):
            run_python(overflowing)
        result = self.rust_result(overflowing)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_packet_bytes_and_result_are_deterministic(self) -> None:
        duplicate = Path(self.temp.name) / "duplicate.input.bin"
        header, records = fixture_data(FIXTURE)
        write_packet(duplicate, header, records)
        self.assertEqual(duplicate.read_bytes(), self.packet.read_bytes())
        first = self.rust_result()
        second = self.rust_result(duplicate)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(canonical_bytes(json.loads(first.stdout)), canonical_bytes(json.loads(second.stdout)))

    def test_opt_in_metrics_preserve_exact_output_and_cover_the_input(self) -> None:
        from applications.malecns_profile_census.benchmark import parse_sample
        header, records = fixture_data(FIXTURE)
        edge_count = sum(len(record["edges"]) for record in records)
        expected = canonical_bytes(run_python(self.packet))
        for command in (
            [str(self.binary), str(self.packet), "--metrics"],
            [sys.executable, "-B", "-m", "applications.malecns_profile_census.oracle", str(self.packet), "--metrics"],
        ):
            with self.subTest(command=command[0]):
                completed = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, check=True)
                result, metrics, _ = parse_sample(completed.stdout, completed.stderr, header, edge_count)
                self.assertEqual(canonical_bytes(result), expected)
                self.assertEqual(metrics["edge_count"], edge_count)


if __name__ == "__main__":
    unittest.main()
