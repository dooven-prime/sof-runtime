import copy
import json
from pathlib import Path
import tempfile
import unittest

from applications.shared_a0_extraction_review.review import compare_runs, core_boundary


class ExtractionReviewTests(unittest.TestCase):
    def paired(self, left, right):
        with tempfile.TemporaryDirectory() as directory:
            a, b = (Path(directory)/n for n in ("old.json", "new.json"))
            a.write_text(json.dumps(left)); b.write_text(json.dumps(right))
            return compare_runs(a, b)

    def record(self):
        observation = {"status": "MATCHED_BYTES", "matching_observation_admissible": True,
                       "application_decision": "NOT_ASSESSED", "process": {"actually_killed": False, "changed_during_observation": False},
                       "result": {"status": "INTEGRITY_MATCHES", "source_trust": "NOT_ASSESSED", "application_decision": "NOT_ASSESSED",
                                  "validity": "OBSERVED_INTERVAL_ONLY", "inspection": {"entries": [], "manifest_utf8": "{}", "manifest_sha256": "a",
                                  "bindings_sha256": "b", "byte_passes": 2, "backend": "windows-ntfs.v0"}}}
        return {"cases": [{"name": "normal", "kind": "normal", "observation": observation}]}

    def test_comparator_ignores_attempt_metadata_not_byte_semantics(self):
        a = self.record(); b = copy.deepcopy(a)
        b["cases"][0]["observation"]["process"]["pid"] = 999
        self.assertEqual(self.paired(a, b)["cases"], 1)
        b["cases"][0]["observation"]["result"]["inspection"]["manifest_utf8"] = "[]"
        with self.assertRaisesRegex(ValueError, "inventory/codec bytes changed"): self.paired(a, b)

    def test_comparator_rejects_missing_case_or_changed_classification(self):
        a = self.record()
        with self.assertRaisesRegex(ValueError, "matrix changed"): self.paired(a, {"cases": []})
        for x in (a["cases"][0]["observation"],):
            x["status"] = "REJECTED"; x["matching_observation_admissible"] = False
            x["result"] = {"status": "REJECTED", "source_trust": "NOT_ASSESSED", "application_decision": "NOT_ASSESSED",
                           "error": {"class": "REJECTED", "code": "LENGTH"}}
        b = copy.deepcopy(a); b["cases"][0]["observation"]["result"]["error"]["code"] = "DIGEST_MISMATCH"
        with self.assertRaisesRegex(ValueError, "classification changed"): self.paired(a, b)

    def test_single_mechanical_source_boundary(self):
        r = core_boundary()
        self.assertEqual(set(r["top_level_modules"]), {"identity", "codec", "inventory"})
        self.assertTrue(r["independent_python_reference_retained"])


if __name__ == "__main__": unittest.main()
