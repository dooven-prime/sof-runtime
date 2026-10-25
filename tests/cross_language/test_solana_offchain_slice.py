"""Offline projection, real process-kill recovery and fail-closed controls."""
from copy import deepcopy
from pathlib import Path
import subprocess
import tempfile
from time import perf_counter,sleep
import unittest

from applications.solana_offchain_slice.common import canonical,parse,sha
from applications.solana_offchain_slice.fixtures import synthetic,change_response,b58
from applications.solana_offchain_slice.reference import load_capture,projection
from applications.solana_offchain_slice.runner import POINTS,binary,build,invoke


class SolanaSliceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): build()

    def test_projection_versions_loaded_addresses_errors_duplicates_and_unlisted(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);manifest=synthetic(root/"capture");expected=projection(manifest)
            result,_=invoke(manifest,root/"state",root,"clean")
            self.assertEqual(result["status"],"COMPLETED_LOCAL_CAPTURE")
            self.assertEqual((root/"state/projection.jsonl").read_bytes(),expected)
            records=[parse(line) for line in expected.splitlines()]
            self.assertEqual(len(records),7)
            self.assertEqual(records[3],{"kind":"not_listed_by_source","slot":101})
            self.assertEqual(records[2]["instructions"][0]["program_id"],b58(4))
            self.assertEqual(records[2]["error"],{"InstructionError":[0,{"Custom":42}]})
            self.assertEqual([r["transaction_index"] for r in records if r["slot"]==102 and r["kind"]=="transaction"],[0,1])

    def test_repeated_execution_is_a_verified_noop(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);manifest=synthetic(root/"capture");state=root/"state"
            first,_=invoke(manifest,state,root,"first")
            before={p.name:p.read_bytes() for p in state.iterdir()}
            second,_=invoke(manifest,state,root,"second")
            self.assertEqual(first["projection_sha256"],second["projection_sha256"])
            self.assertEqual(second["resumed_from_index"],3)
            self.assertEqual(before,{p.name:p.read_bytes() for p in state.iterdir()})

    def test_actual_kill_and_restart_at_all_six_boundaries(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);manifest=synthetic(root/"capture");expected=projection(manifest)
            for point in POINTS:
                with self.subTest(point=point):
                    slot=102 if "projection" in point else 100;state=root/point
                    _,process=invoke(manifest,state,root,f"{point}-kill",(point,slot))
                    self.assertTrue(process["terminated_at_boundary"])
                    result,_=invoke(manifest,state,root,f"{point}-resume")
                    self.assertEqual(result["status"],"COMPLETED_LOCAL_CAPTURE")
                    self.assertEqual((state/"projection.jsonl").read_bytes(),expected)
                    if point in ("segment_publish","partial_checkpoint"):
                        self.assertEqual(result["orphan_segments_adopted"],1)

    def test_unknown_version_rpc_error_null_metadata_and_indices_fail(self):
        mutations=[lambda r:r["result"]["transactions"][0].update(version=1),
                   lambda r:r.update(error={"code":-32015,"message":"unsupported"}),
                   lambda r:r.update(result=None),
                   lambda r:r["result"]["transactions"][0].update(meta=None),
                   lambda r:r["result"]["transactions"][0]["transaction"]["message"]["instructions"][0].update(programIdIndex=250),
                   lambda r:r["result"]["transactions"][1]["meta"].pop("loadedAddresses"),
                   lambda r:r["result"]["transactions"][1]["meta"]["loadedAddresses"].update(writable=[]),
                   lambda r:r["result"]["transactions"][0]["transaction"].update(signatures=["not-base58!"])]
        for index,mutate in enumerate(mutations):
            with self.subTest(index=index),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);manifest=synthetic(root/"capture");change_response(manifest,"block-100",mutate)
                with self.assertRaises((ValueError,TypeError,KeyError)):load_capture(manifest)
                result,_=invoke(manifest,root/"state",root,"rejected")
                self.assertEqual(result["status"],"UNRESOLVED")
                self.assertFalse((root/"state/checkpoint.json").exists())

    def test_range_index_config_root_cluster_and_chain_fail_closed(self):
        cases=[("index_after",lambda r:r.update(result=[100])),
               ("root_before",lambda r:r.update(result=99)),
               ("genesis_after",lambda r:r.update(result=b58(500))),
               ("block-102",lambda r:r["result"].update(previousBlockhash=b58(7))),
               ("block-102",lambda r:r["result"].update(parentSlot=101))]
        for role,mutate in cases:
            with self.subTest(role=role),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);manifest=synthetic(root/"capture");change_response(manifest,role,mutate)
                with self.assertRaises(ValueError):load_capture(manifest)
                result,_=invoke(manifest,root/"state",root,"bad")
                self.assertEqual(result["status"],"UNRESOLVED")

    def test_byte_hash_duplicate_json_and_manifest_path_escape_fail(self):
        for kind in ("hash","duplicate","path"):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);manifest=synthetic(root/"capture");m=parse(manifest.read_bytes());item=m["rpc"]["block-100"]
                target=manifest.parent/item["response"]
                if kind=="hash":target.write_bytes(target.read_bytes()+b" ")
                elif kind=="duplicate":
                    raw=b'{"jsonrpc":"2.0","jsonrpc":"2.0","id":9,"result":null}'
                    target.write_bytes(raw);item["response_sha256"]=sha(raw);manifest.write_bytes(canonical(m))
                else:
                    item["response"]="../outside.json";manifest.write_bytes(canonical(m))
                with self.assertRaises((ValueError,FileNotFoundError)):load_capture(manifest)
                result,_=invoke(manifest,root/"state",root,"bad")
                self.assertEqual(result["status"],"UNRESOLVED")

    def test_corrupt_checkpoint_segments_and_foreign_state_are_not_repaired(self):
        for kind in ("checkpoint","segment","aggregate","foreign"):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);manifest=synthetic(root/"capture");state=root/"state"
                invoke(manifest,state,root,"first")
                if kind=="checkpoint":
                    p=state/"checkpoint.json";value=parse(p.read_bytes());value["next_index"]=1;p.write_bytes(canonical(value))
                elif kind=="segment":(state/"slot-100.jsonl").write_bytes(b"damaged\n")
                elif kind=="aggregate":(state/"projection.jsonl").write_bytes(b"damaged\n")
                else:(state/"unexpected.txt").write_text("foreign")
                result,_=invoke(manifest,state,root,"bad")
                self.assertEqual(result["status"],"UNRESOLVED")

    def test_changed_capture_cannot_resume_the_old_state(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);manifest=synthetic(root/"capture");state=root/"state"
            invoke(manifest,state,root,"first")
            m=parse(manifest.read_bytes());m["source"]="synthetic://different-binding";manifest.write_bytes(canonical(m))
            result,_=invoke(manifest,state,root,"changed")
            self.assertEqual(result["status"],"UNRESOLVED")
            self.assertIn("identity",result["detail"])

    def test_manifest_contract_types_range_and_finality_are_not_coerced(self):
        for kind in ("boolean-version","boolean-id","commitment","range","duplicate-slot"):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);manifest=synthetic(root/"capture");m=parse(manifest.read_bytes())
                if kind=="boolean-version":m["config"]["maxSupportedTransactionVersion"]=False
                elif kind=="boolean-id":m["rpc"]["version"]["id"]=True
                elif kind=="commitment":m["commitment"]="confirmed"
                elif kind=="range":m["end_slot"]=116
                else:m["listed_blocks"].append(deepcopy(m["listed_blocks"][-1]))
                manifest.write_bytes(canonical(m))
                with self.assertRaises(ValueError):load_capture(manifest)
                result,_=invoke(manifest,root/"state",root,"bad")
                self.assertEqual(result["status"],"UNRESOLVED")

    def test_concurrent_writer_is_refused_without_stealing_lock(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);manifest=synthetic(root/"capture");state=root/"state"
            with (root/"held.txt").open("wb") as stream:
                child=subprocess.Popen([str(binary()),str(manifest),str(state),"--pause","segment_publish","100"],stdout=stream,stderr=subprocess.PIPE)
                try:
                    start=perf_counter()
                    while b"FAULT_REACHED" not in (root/"held.txt").read_bytes():
                        if child.poll() is not None or perf_counter()-start>15: self.fail("writer did not pause")
                        sleep(.01)
                    result,_=invoke(manifest,state,root,"second-writer")
                    self.assertEqual(result["status"],"UNRESOLVED")
                    self.assertIn("writer",result["detail"])
                finally:
                    if child.poll() is None:child.kill()
                    child.communicate(timeout=5)
            result,_=invoke(manifest,state,root,"recovered")
            self.assertEqual(result["status"],"COMPLETED_LOCAL_CAPTURE")


if __name__=="__main__":unittest.main()
