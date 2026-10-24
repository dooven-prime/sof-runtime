"""Coverage, binding and cross-shard controls; no timing acceptance claims."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from applications.event_causal_consumers.q2.engine import check
from applications.event_causal_consumers.q2.replay import verify_rejection
from applications.event_causal_consumers.q2_examples import controls, request, P, F, O, A, GAMMA, COUNT, PARITY, pair, lit, op, field, fold, var, case, fst, snd, choose
from applications.event_causal_consumers.parallel_v0.coordinator import (
    build_worker, canonical, execute, prepare_plan, reduce_plan, run_task,
    sha, source_closure, task_for, worker_binary,
)


class ParallelQ2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build_worker()

    def tasks(self, raw, shards=3):
        plan = prepare_plan(raw, shards)
        with tempfile.TemporaryDirectory() as directory:
            results = [run_task(task_for(plan, shard), Path(directory)/f"{i}.json") for i, shard in enumerate(plan["shards"])]
        self.assertTrue(all(result["status"] == "COMPLETE" for result in results), results)
        return plan, results

    def test_existing_nine_controls_and_independent_replay(self):
        for name, raw in controls().items():
            serial = check(raw)
            for shards in (2, 3, 4):
                with self.subTest(name=name, shards=shards):
                    plan, results = self.tasks(raw, shards)
                    result = reduce_plan(raw, plan, results)
                    self.assertEqual(result.get("q2_status"), serial["status"], result)
                    self.assertTrue(result["coverage_complete"])
                    self.assertTrue(result["reference_check"])
                    if result["status"] == "FAIL":
                        self.assertEqual(result["rejection"]["witness"]["clause"], serial["witness"]["clause"])
                        self.assertEqual(verify_rejection(raw, result["rejection"])["status"], "VALID_REJECTION_WITNESS")

    def test_local_complete_and_conflict_free_is_not_global_pass(self):
        raw = controls()["forget_ports"]
        # Four actual registered states, four admitted singleton shards.
        plan, results = self.tasks(raw, 4)
        self.assertTrue(all(len(shard["members"]) == 1 for shard in plan["shards"]))
        self.assertTrue(all(result["local_conflicts"] == [] for result in results))
        self.assertEqual(reduce_plan(raw, plan, results)["status"], "FAIL")
        self.assertTrue(all("PASS" not in result.values() for result in results))

    def test_missing_duplicate_binding_and_coverage_faults_are_unresolved(self):
        raw = controls()["packet_only"]
        plan, results = self.tasks(raw)
        bad_cases = [results[:-1], results+[results[0]], [results[0], results[0], results[2]]]
        changed = deepcopy(results); changed[0]["binding"]["versions"]["encoding"] = "wrong"; bad_cases.append(changed)
        changed = deepcopy(results); changed[0]["task_input_sha256"] = "0"*64; bad_cases.append(changed)
        changed = deepcopy(results); changed[0]["coverage_digest"] = "0"*64; bad_cases.append(changed)
        changed = deepcopy(results); changed[0]["fiber_records"].pop(); bad_cases.append(changed)
        changed = deepcopy(results); changed[0]["fiber_records"][0]["members"] *= 2; bad_cases.append(changed)
        changed = deepcopy(results); changed[0]["fiber_records"][0]["witness_state_id"] = False; bad_cases.append(changed)
        changed = deepcopy(results); changed[0]["fiber_records"][0]["members"][0] = plan["shards"][1]["members"][0]; bad_cases.append(changed)
        changed = deepcopy(results); changed[0] = {"status":"UNRESOLVED","reason":"WORKER_CRASH"}; bad_cases.append(changed)
        for index, bad in enumerate(bad_cases):
            with self.subTest(index=index):
                self.assertEqual(reduce_plan(raw, plan, bad)["status"], "UNRESOLVED")

    def test_coordinated_forged_plan_cannot_claim_coverage(self):
        raw = controls()["packet_only"]
        plan, results = self.tasks(raw)
        plan["states"].pop()
        plan["binding"]["domain_sha256"] = sha(plan["states"])
        plan["plan_id"] = "forged"
        self.assertEqual(reduce_plan(raw, plan, results)["status"], "UNRESOLVED")

    def test_forged_signature_or_history_and_failed_replay_cannot_pass(self):
        raw = controls()["forget_origin"]
        plan, results = self.tasks(raw)
        changed = deepcopy(results)
        changed[0]["fiber_records"][0]["signature"]["reports"][0]["value"]["value"] = []
        self.assertEqual(reduce_plan(raw, plan, changed)["status"], "UNRESOLVED")
        changed_plan = deepcopy(plan); changed_plan["states"][0]["word"] = ""
        self.assertEqual(reduce_plan(raw, changed_plan, results)["status"], "UNRESOLVED")
        with patch("applications.event_causal_consumers.parallel_v0.coordinator.verify_rejection",
                   return_value={"status":"INVALID_REJECTION_WITNESS"}):
            self.assertEqual(reduce_plan(raw, plan, results)["status"], "UNRESOLVED")

    def test_empty_registration_limits_and_scope_never_pass(self):
        raw = request(2); raw["selected"] = [0]
        self.assertEqual(execute(raw)["status"], "UNRESOLVED")
        for resources in ({"max_states":1}, {"max_steps":1}, {"max_ast_nodes":1}, {"max_seconds":1e-30}):
            raw = request(4); raw["resources"] = resources
            result = execute(raw)
            self.assertEqual(result["status"], "UNRESOLVED")
            self.assertFalse(result["domain_complete"])
        raw = request(4); raw["environment"] = {"defect":[0,0,1,2,3],"seed":list(range(5))}
        self.assertEqual(execute(raw)["status"], "UNRESOLVED")

    def test_actual_worker_exit_timeout_and_launch_failure(self):
        raw = request(2)
        plan = prepare_plan(raw, 2)
        task = task_for(plan, plan["shards"][0])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"task.json"
            self.assertEqual(run_task(task, path, timeout=1e-9)["status"], "UNRESOLVED")
            with patch("applications.event_causal_consumers.parallel_v0.coordinator.worker_binary", return_value=Path(directory)/"missing"):
                self.assertEqual(run_task(task, path)["status"], "UNRESOLVED")
            path.write_bytes(b"not json")
            child = subprocess.run([str(worker_binary()),str(path)],capture_output=True,timeout=10)
            self.assertNotEqual(child.returncode,0)

    def test_killed_workers_cannot_produce_global_pass(self):
        original = subprocess.Popen
        def killed(*args, **kwargs):
            process = original(*args, **kwargs)
            process.kill()
            return process
        with patch("applications.event_causal_consumers.parallel_v0.coordinator.subprocess.Popen", side_effect=killed):
            result = execute(controls()["packet_only"],3)
        self.assertEqual(result["status"],"UNRESOLVED")
        self.assertFalse(result["coverage_complete"])

    def test_source_drift_existing_directory_and_receipt_tampering(self):
        from applications.event_causal_consumers.parallel_v0.coordinator import file_sha, load_json, verify_run
        closure = source_closure()
        with patch("applications.event_causal_consumers.parallel_v0.coordinator.source_closure",
                   side_effect=[closure,closure,{**closure,"worker_binary":"changed"}]):
            self.assertEqual(execute(controls()["packet_only"])["status"],"UNRESOLVED")
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/"new"
            result=execute(controls()["packet_only"],3,target)
            self.assertEqual(result["status"],"PASS")
            self.assertEqual(verify_run(target)["status"],"VERIFIED_LOCAL_CLOSURE")
            # Existing output must not be overwritten, even for the same input.
            original=(target/"decision.json").read_bytes()
            self.assertEqual(execute(controls()["packet_only"],3,target)["status"],"UNRESOLVED")
            self.assertEqual((target/"decision.json").read_bytes(),original)
            changed=load_json(original); changed["q_states"]+=1
            (target/"decision.json").write_bytes(canonical(changed))
            receipt=load_json((target/"receipt.json").read_bytes())
            receipt["files"]["decision.json"]=file_sha(target/"decision.json")
            (target/"receipt.json").write_bytes(canonical(receipt))
            self.assertEqual(verify_run(target)["status"],"UNRESOLVED")

    def test_receipt_binds_exact_files_and_no_product_admission(self):
        from applications.event_causal_consumers.parallel_v0.coordinator import file_sha, load_json
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/"new"
            result = execute(controls()["packet_only"], 3, target)
            self.assertEqual(result["status"], "PASS", result)
            receipt = load_json((target/"receipt.json").read_bytes())
            for name, expected in receipt["files"].items():
                self.assertEqual(file_sha(target/name), expected)
            self.assertFalse(receipt["performance_claim"])
            self.assertFalse(result["canonical_compiler_admission"])

    def test_typed_values_big_nats_options_labels_and_atom_renaming(self):
        cases = [request(3, {"kind":"none","element_type":"Nat"}, [], [
            {"label":"first","letter":"p","guard":lit("Bool",True)},
            {"label":"second","letter":"p","guard":lit("Bool",True)}]),
            request(3, GAMMA, [{"label":"large","expr":op("add",lit("Nat",2**120),lit("Nat",2**120))}])]
        renamed = request(2); renamed["environment"].update(atoms=["a",1],kernel_ports=[1,0]); renamed["selected"]=["a",1]
        cases.append(renamed)
        for raw in cases:
            plan, results = self.tasks(raw)
            self.assertEqual(reduce_plan(raw, plan, results).get("q2_status"),check(raw)["status"])

    def test_all_compiled_constructors_primitives_and_literal_sorts(self):
        some = {"kind":"some","value":lit("Nat",7)}
        none = {"kind":"none","element_type":"Nat"}
        seq = {"kind":"list","element_type":"Nat","items":[lit("Nat",1),lit("Nat",2)]}
        record = {"kind":"record","type":"Origin","fields":{name:field(O,name) for name in ("label","parents","target")}}
        samples = [lit("Nat",3), F, pair(lit("Nat",1),lit("Bool",False)), fst(pair(F,O)), snd(pair(F,O)),
                   choose(lit("Bool",True),lit("Nat",3),lit("Nat",4)),
                   fold(seq,lit("Nat",0),"acc","item",op("add",var("acc"),var("item"))),
                   record, field(record,"parents"),seq,some,none,case(some,lit("Nat",0),"x",var("x")),
                   case(none,lit("Nat",0),"x",var("x"))]
        primitives = [op("eq",lit("Atom",1),lit("Atom",1)),op("not",lit("Bool",False)),
                      op("and",lit("Bool",True),lit("Bool",False)),op("or",lit("Bool",False),lit("Bool",True)),
                      op("add",lit("Nat",3),lit("Nat",4)),op("lt",lit("Nat",3),lit("Nat",4)),
                      op("le",lit("Nat",4),lit("Nat",4)),op("mod",lit("Nat",7),modulus=3),
                      op("union",lit("Block",[0]),lit("Block",[1])),
                      op("intersection",lit("Block",[0]),lit("Block",[1])),op("subset",lit("Block",[0]),F),
                      op("cardinality",F),op("cons",lit("Nat",0),seq),op("lookup",P,lit("Pos",0)),
                      op("entries",P),op("carrier",P,F),op("f_p",lit("Pos",2)),op("f_d",lit("Pos",1))]
        literals = {"Bool":True,"Nat":0,"Atom":1,"Pos":1,"Letter":"d","Block":[0],
                    "Partition":[[0,[0]],[1,[1]],[2,[2]]],
                    "Origin":{"label":"d","parents":[[0,[0]],[2,[2]]],"target":0},
                    "AbsRecord":{"label":"d","carrier_at":0,"carrier":[0],"partner_at":2,
                                 "partner":[2],"target":0,"merged":[0,2]}}
        samples += primitives + [lit(name,value) for name,value in literals.items()]
        samples += [lit(["Prod","Nat","Bool"],[1,False]),lit(["List","Nat"],[1,2]),
                    lit(["Option","Nat"],{"some":7}),lit(["Option","Nat"],None)]
        from applications.event_causal_consumers.q2.syntax import NODE_KINDS, OPERATIONS
        seen = set()
        def visit(value):
            if isinstance(value,dict):
                if "kind" in value: seen.add(value["kind"])
                for item in value.values(): visit(item)
            elif isinstance(value,list):
                for item in value: visit(item)
        for sample in samples: visit(sample)
        self.assertEqual(seen,NODE_KINDS)
        self.assertEqual({sample["name"] for sample in primitives},OPERATIONS)
        raw = request(3,GAMMA,[{"label":f"report-{i}","expr":sample} for i,sample in enumerate(samples)])
        plan,results = self.tasks(raw,3)
        self.assertEqual(reduce_plan(raw,plan,results)["status"],"PASS")

    def test_clause_priority_is_global_and_worker_limits_are_unresolved(self):
        raw = request(4,PARITY,[{"label":"partition","expr":P}],
                      [{"label":"raw-d","letter":"d","guard":lit("Bool",True)}])
        plan,results = self.tasks(raw)
        result = reduce_plan(raw,plan,results)
        self.assertEqual(result["q2_status"],"FAIL_READ")
        task = task_for(plan,plan["shards"][0])
        task["input"]["max_steps"] = 1
        task["input_sha256"] = sha(task["input"])
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(run_task(task,Path(directory)/"limited.json")["status"],"UNRESOLVED")


if __name__ == "__main__":
    unittest.main()
