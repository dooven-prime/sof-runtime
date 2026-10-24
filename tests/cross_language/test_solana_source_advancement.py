"""Offline source identity, explicit reapproval and refusal atomicity controls."""
from pathlib import Path
import shutil
import tempfile
import unittest

from applications.solana_offchain_slice.common import canonical, file_sha, parse, sha
from applications.solana_incremental_replay.fixtures import synthetic
from applications.solana_source_advancement.fixtures import corpus, request
from applications.solana_source_advancement.reference import evaluate, check_success
from applications.solana_source_advancement.runner import binary, build, invoke, tree_hashes


class SourceAdvancementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build()

    def setup_domain(self, root):
        return corpus(synthetic(root/"upstream"), root/"corpus", small=True)

    def checked(self, root, name, req, destination):
        ref_path = root/f"{name}.reference-request.json"; ref_path.write_bytes(canonical(req))
        predicted = evaluate(ref_path, destination, file_sha(binary()))
        parent = Path(req["old_state"]) if req["old_state"] else None
        before = tree_hashes(parent) if parent else None
        existed = tree_hashes(destination) if Path(destination).exists() else None
        actual, process = invoke(req, destination, root/"logs", name)
        self.assertEqual(actual["status"], predicted["status"], (actual, predicted))
        self.assertEqual(actual["earliest_conflict_slot"], predicted["earliest_conflict_slot"])
        if actual["status"] == "COMPLETED_OFFLINE_ADVANCEMENT":
            check_success(predicted, actual, destination)
            self.assertEqual(process["returncode"], 0)
        else:
            self.assertFalse(actual["published"])
            self.assertIsNone(actual["new_checkpoint_sha256"])
            self.assertTrue(actual["reason"])
            if existed is None:
                self.assertFalse(Path(destination).exists())
            else:
                self.assertEqual(tree_hashes(destination), existed)
        if parent:
            self.assertEqual(tree_hashes(parent), before)
        self.assertFalse(list(root.glob(".*.staging-*")))
        return actual

    def base(self, root, domain, count=2):
        state = root/"initial"
        actual = self.checked(root, "init", request(domain["policy"], domain["captures"][f"a-{count}"], "init"), state)
        return state, actual["new_checkpoint_sha256"], actual

    def test_append_preserves_prefix_and_three_identities(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); d = self.setup_domain(root)
            first = self.checked(root, "one", request(d["policy"], d["captures"]["a-1"], "init"), root/"one")
            second = self.checked(root, "two", request(d["policy"], d["captures"]["a-2"], "append", d["captures"]["a-1"], root/"one", first["new_checkpoint_sha256"]), root/"two")
            third = self.checked(root, "three", request(d["policy"], d["captures"]["a-3"], "append", d["captures"]["a-2"], root/"two", second["new_checkpoint_sha256"]), root/"three")
            full = self.checked(root, "full", request(d["policy"], d["captures"]["a-3"], "init"), root/"full")
            self.assertEqual((root/"three/projection.jsonl").read_bytes(), (root/"full/projection.jsonl").read_bytes())
            self.assertEqual(first["source_identity_sha256"], third["source_identity_sha256"])
            self.assertEqual(first["execution_identity_sha256"], third["execution_identity_sha256"])
            self.assertNotEqual(first["new_checkpoint_sha256"], second["new_checkpoint_sha256"])
            self.assertNotEqual(third["new_checkpoint_sha256"], full["new_checkpoint_sha256"])
            self.assertEqual(second["work"]["candidate_prefix_decoded_slots"], [])
            self.assertEqual(third["work"]["candidate_prefix_decoded_slots"], [])
            self.assertEqual(third["work"]["candidate_suffix_decoded_slots"], [102])

    def test_new_credential_requires_explicit_allowed_reapproval(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); d = self.setup_domain(root); state, anchor, first = self.base(root, d)
            denied = self.checked(root, "denied", request(d["policy"], d["captures"]["b-full"], "append", d["captures"]["a-2"], state, anchor), root/"denied")
            self.assertEqual(denied["reason"], "SOURCE_OR_PREFIX_EVIDENCE_REAPPROVAL_REQUIRED")
            approved = self.checked(root, "approved", request(d["policy"], d["captures"]["b-full"], "reapprove", d["captures"]["a-2"], state, anchor), root/"approved")
            self.assertNotEqual(first["source_identity_sha256"], approved["source_identity_sha256"])
            self.assertEqual(first["execution_identity_sha256"], approved["execution_identity_sha256"])
            self.assertEqual(approved["work"]["candidate_prefix_decoded_slots"], [100])
            self.assertEqual(approved["compatibility"], "REAPPROVED_EQUAL_RECORDS")

    def test_same_source_unprojected_evidence_change_is_not_free_inheritance(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); d = self.setup_domain(root); state, anchor, first = self.base(root, d)
            denied = self.checked(root, "denied", request(d["policy"], d["captures"]["raw-revision"], "append", d["captures"]["a-2"], state, anchor), root/"denied")
            self.assertEqual(denied["reason"], "SOURCE_OR_PREFIX_EVIDENCE_REAPPROVAL_REQUIRED")
            approved = self.checked(root, "approved", request(d["policy"], d["captures"]["raw-revision"], "reapprove", d["captures"]["a-2"], state, anchor), root/"approved")
            self.assertEqual(first["source_identity_sha256"], approved["source_identity_sha256"])
            self.assertTrue(approved["source_transition"]["prefix_evidence_changed"])

    def test_earliest_record_and_listed_status_conflicts_are_not_reorgs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); d = self.setup_domain(root); state, anchor, _ = self.base(root, d)
            for name, kind in (("conflict", "CANONICAL_RECORDS"), ("listed-conflict", "LISTED_STATUS")):
                result = self.checked(root, name, request(d["policy"], d["captures"][name], "reapprove", d["captures"]["a-2"], state, anchor), root/name)
                self.assertEqual(result["status"], "REJECTED_PREFIX_CONFLICT")
                self.assertEqual(result["earliest_conflict_slot"], 100)
                self.assertEqual(result["conflict"]["kind"], kind)
                self.assertEqual(result["affected_checkpoint_sha256"], anchor)
                self.assertEqual(result["compatibility"], "INCOMPATIBLE_WITH_PROPOSED_CAPTURE")

    def test_missing_evidence_continuity_and_unknown_source_refuse_without_commit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); d = self.setup_domain(root); state, anchor, _ = self.base(root, d)
            for name in ("bad-continuity", "unknown"):
                result = self.checked(root, name, request(d["policy"], d["captures"][name], "reapprove", d["captures"]["a-2"], state, anchor), root/name)
                self.assertEqual(result["status"], "UNRESOLVED")
            for name, missing in (("admission", "admission.json"), ("payload", "block-102.response.json")):
                copy = root/f"capture-{name}"; shutil.copytree(d["captures"]["a-3"].parent, copy)
                (copy/missing).unlink()
                result = self.checked(root, name, request(d["policy"], copy/"manifest.json", "append", d["captures"]["a-2"], state, anchor), root/name)
                self.assertEqual(result["status"], "UNRESOLVED")

    def test_bad_anchors_range_shrink_parent_corruption_and_existing_destination(self):
        for kind in ("parent-anchor", "policy-anchor", "shrink", "corrupt-segment", "foreign-execution", "cursor", "destination"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); d = self.setup_domain(root); state, anchor, _ = self.base(root, d)
                candidate = d["captures"]["a-1" if kind == "shrink" else "a-3"]
                req = request(d["policy"], candidate, "append", d["captures"]["a-2"], state, anchor)
                if kind == "parent-anchor": req["old_checkpoint_sha256"] = "0"*64
                elif kind == "policy-anchor": req["policy_sha256"] = "0"*64
                elif kind == "corrupt-segment":
                    copy = root/"corrupt-parent"; shutil.copytree(state, copy); (copy/"slot-100.jsonl").write_bytes(b"broken\n"); req["old_state"] = str(copy)
                elif kind in ("foreign-execution", "cursor"):
                    copy = root/"foreign-parent"; shutil.copytree(state, copy); cp = copy/"checkpoint.json"; frame = parse(cp.read_bytes())
                    if kind == "foreign-execution": frame["body"]["execution_identity"]["program_sha256"] = "f"*64
                    else: frame["body"]["next_index"] = True
                    frame["body_sha256"] = sha(canonical(frame["body"])); cp.write_bytes(canonical(frame)); req["old_state"] = str(copy)
                    req["old_checkpoint_sha256"] = file_sha(cp)
                destination = root/"attempt"
                if kind == "destination": destination.mkdir(); (destination/"retain.txt").write_text("retain")
                result = self.checked(root, "attempt", req, destination)
                self.assertEqual(result["status"], "UNRESOLVED")

    def test_reapproval_permission_cannot_be_inferred_from_equal_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); d = self.setup_domain(root)
            policy = parse(d["policy"].read_bytes()); policy["reapproval_pairs"] = []
            d["policy"].write_bytes(canonical(policy))
            state, anchor, _ = self.base(root, d)
            result = self.checked(root, "denied", request(d["policy"], d["captures"]["b-full"], "reapprove", d["captures"]["a-2"], state, anchor), root/"denied")
            self.assertEqual(result["status"], "UNRESOLVED")
            self.assertEqual(result["reason"], "SOURCE_REAPPROVAL_PAIR_NOT_ALLOWED")

    def test_output_cannot_add_even_a_lock_to_parent_or_capture(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); d = self.setup_domain(root); state, anchor, _ = self.base(root, d)
            old_capture = d["captures"]["a-2"].parent
            candidate = d["captures"]["a-3"]
            snapshots = {p: tree_hashes(p) for p in (state, old_capture, candidate.parent)}
            for index, parent in enumerate((state, old_capture, candidate.parent)):
                req = request(d["policy"], candidate, "append", d["captures"]["a-2"], state, anchor)
                result = self.checked(root, f"inside-{index}", req, parent/"forbidden-output")
                self.assertEqual(result["status"], "UNRESOLVED")
                for path, snapshot in snapshots.items():
                    self.assertEqual(tree_hashes(path), snapshot)
            req = request(d["policy"], candidate, "init", d["captures"]["a-2"], state, anchor)
            result = self.checked(root, "invalid-init", req, state/"forbidden-init")
            self.assertEqual(result["reason"], "INIT_HAS_PARENT")
            self.assertEqual(tree_hashes(state), snapshots[state])


if __name__ == "__main__":
    unittest.main()
