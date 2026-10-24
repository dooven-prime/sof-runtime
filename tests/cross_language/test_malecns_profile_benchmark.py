from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from applications.malecns_profile_census.benchmark import (
    PHASES, controlled_environment, parse_sample, run_child, summarize,
)
from applications.malecns_profile_census.oracle import run
from applications.malecns_profile_census.prepare_input import fixture_data
from applications.malecns_profile_census.protocol import canonical_bytes, write_packet


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "examples/malecns_profile_census/tiny-fixture.json"


class ProfileBenchmarkTests(unittest.TestCase):
    def test_diagnostics_cannot_substitute_an_incomplete_domain(self) -> None:
        header, records = fixture_data(FIXTURE)
        edge_count = sum(len(row["edges"]) for row in records)
        with tempfile.TemporaryDirectory() as directory:
            packet = Path(directory) / "fixture.bin"
            write_packet(packet, header, records)
            metrics = {}
            result = run(packet, metrics=metrics)
        metrics["serialize_seconds"] = 0.0
        stdout = canonical_bytes(result)

        def diagnostic(value):
            return ("SOF_PROFILE_METRICS " + json.dumps(value)).encode()

        _, _, digest = parse_sample(stdout, diagnostic(metrics), header, edge_count)
        self.assertEqual(len(digest), 64)
        for key, value in (("edge_count", edge_count - 1), ("record_count", 0),
                           ("serialize_seconds", -1), ("serialize_seconds", float("nan"))):
            with self.subTest(key=key, value=value):
                with self.assertRaises(ValueError):
                    parse_sample(stdout, diagnostic({**metrics, key: value}), header, edge_count)
        with self.assertRaises(ValueError):
            parse_sample(stdout, diagnostic(metrics) + b"\nextra", header, edge_count)

    def test_summary_keeps_process_and_phase_intervals_distinct(self) -> None:
        samples = []
        for implementation, walls, phases in (("python", [4., 8., 6.], .1), ("rust", [2., 1., 3.], .05)):
            for wall in walls:
                samples.append({
                    "implementation": implementation, "process_wall_seconds": wall,
                    **{key: phases for key in PHASES}, "max_observed_rss_bytes": 100,
                    "max_observed_os_peak_working_set_bytes": None,
                })
        result = summarize(samples)
        self.assertEqual(result["python_over_rust_median_process_wall_ratio"], 3.)
        self.assertEqual(result["python"]["process_wall_seconds"]["median"], 6.)
        self.assertEqual(result["python"]["stream_decode_validate_aggregate_seconds"]["median"], .1)
        self.assertIsNone(result["rust"]["maximum_observed_os_peak_working_set_bytes"])
        with self.assertRaises(ValueError):
            summarize([])

    def test_thread_policy_does_not_mutate_the_calling_environment(self) -> None:
        before = dict(os.environ)
        env = controlled_environment()
        self.assertEqual(dict(os.environ), before)
        self.assertNotIn("PYTHONOPTIMIZE", env)
        self.assertEqual(env["OPENBLAS_NUM_THREADS"], "1")
        self.assertEqual(env["RAYON_NUM_THREADS"], "1")

    def test_failed_limited_and_successful_processes_are_distinct(self) -> None:
        stdout, _, measurements = run_child([sys.executable, "-c", "print('complete')"])
        self.assertEqual(stdout.strip(), b"complete")
        self.assertGreater(measurements["process_wall_seconds"], 0)
        self.assertGreater(measurements["memory_observations"], 0)
        with self.assertRaises(RuntimeError):
            run_child([sys.executable, "-c", "raise SystemExit(3)"])
        with self.assertRaises(TimeoutError):
            run_child([sys.executable, "-c", "import time; time.sleep(2)"], timeout=.05)
        with self.assertRaises(RuntimeError):
            run_child([sys.executable, "-c", "import time; time.sleep(2)"], rss_limit=1)


if __name__ == "__main__":
    unittest.main()
