import json
from pathlib import Path
import shutil
import subprocess
import unittest

from applications.event_causal_consumers.q2.common import Budget
from applications.event_causal_consumers.q2.model import parse_block, parse_environment, saturate


ROOT = Path(__file__).resolve().parents[2]
CRATE = ROOT / "plugins/rust/event-causal-q2-enumerator"
MANIFEST = CRATE / "Cargo.toml"
BINARY = CRATE / "target/release/event-causal-q2-enumerator"


class RustQ2EnumeratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cargo = shutil.which("cargo")
        if cargo is None:
            raise unittest.SkipTest("Cargo is required for the Rust Q2 cross-check")
        subprocess.run([cargo, "build", "--release", "--locked", "--manifest-path", str(MANIFEST)],
                       cwd=ROOT, check=True, capture_output=True, text=True)

    def test_exact_log_and_gamma_counts_match_python(self):
        expected = {3: (39, 12), 4: (292, 72), 5: (2505, 410), 6: (24306, 2244)}
        for n, (expected_logs, expected_gamma) in expected.items():
            with self.subTest(n=n):
                result = json.loads(subprocess.check_output([str(BINARY), str(n)], text=True))
                defect = [0, 0, *range(2, n)]
                environment = parse_environment({"defect": defect, "seed": list(range(n))})
                selected = parse_block([0, 1], environment, nonempty=True)
                domain = saturate(environment, selected, Budget())
                self.assertEqual(result["status"], "PASS_EXACT")
                self.assertEqual(result["log_states"], len(domain.logs))
                self.assertEqual(result["gamma_count"], len(domain.summaries))
                self.assertEqual((result["log_states"], result["gamma_count"]),
                                 (expected_logs, expected_gamma))


if __name__ == "__main__":
    unittest.main()
