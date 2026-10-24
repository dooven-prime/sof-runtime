"""Fixed-domain Q2 sharding and globally verified fiber reduction."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
from time import perf_counter

from ..q2.common import digest, InputError, ResourceLimit
from ..q2.engine import observation
from ..q2.model import saturate
from ..q2.request import prepare
from ..q2.replay import verify_rejection
from ..q2.syntax import evaluate
from ..q2.values import RECORDS, leaves

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CRATE = ROOT / "plugins/rust/q2-fiber-worker"
SCHEMA = "sof-runtime.q2-parallel.v0"
VERSIONS = {"language": "ECC_SYN_V1", "ir": "Q2_COMPILED_IR_V0",
            "encoding": "Q2_INDEXED_TYPED_VALUES_V0", "worker": "Q2_FIBER_WORKER_V0",
            "domain": "Q2_GLOBAL_LOG_SATURATION_V0", "reducer": "Q2_REFERENCE_REDUCER_V0"}


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()


def load_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise InputError("duplicate JSON key")
            result[key] = value
        return result
    def nonfinite(value):
        raise InputError(f"non-finite JSON number: {value}")
    return json.loads(raw, object_pairs_hook=unique, parse_constant=nonfinite)


def sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def file_sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def worker_binary():
    import os
    return CRATE / "target/release" / ("q2-fiber-worker.exe" if os.name == "nt" else "q2-fiber-worker")


def build_worker():
    subprocess.run(["cargo", "build", "--release", "--locked", "--manifest-path", str(CRATE / "Cargo.toml")],
                   cwd=ROOT, check=True)


def source_closure():
    files = list((HERE.parent / "q2").glob("*.py"))
    files += [HERE / "coordinator.py", HERE / "CONTRACT.md", HERE / "run_controls.py",
              ROOT / "tests/cross_language/test_q2_parallel_fibers.py", HERE.parent / "q2_examples.py",
              CRATE / "src/main.rs", CRATE / "Cargo.toml", CRATE / "Cargo.lock"]
    return {**{path.relative_to(ROOT).as_posix(): file_sha(path) for path in sorted(files)},
            "worker_binary": file_sha(worker_binary()), "python_executable": file_sha(sys.executable),
            "python_version": platform.python_version()}


def bare_wire(value):
    sort, data = value.sort, value.data
    if sort.name == "Nat":
        return str(data)
    if sort.name == "Block":
        return sorted(data)
    if sort.name in ("Prod", "List", "Partition"):
        return [bare_wire(item) for item in data]
    if sort.name == "Option":
        return None if data is None else {"some": bare_wire(data)}
    if sort in RECORDS:
        return {name: bare_wire(item) for (name, _), item in zip(RECORDS[sort], data)}
    return data


def typed_wire(value):
    return {"type": value.sort.json(), "value": bare_wire(value)}


def ir(expr):
    data = expr.data
    if expr.kind == "literal":
        data = bare_wire(data)
    elif expr.kind == "op":
        name, modulus = data
        data = [name, None if modulus is None else str(modulus)]
    return {"kind": expr.kind, "type": expr.sort.json(), "data": data,
            "children": [ir(child) for child in expr.children]}


def _materialize(raw, shards):
    if type(shards) is not int or not 2 <= shards <= 4:
        raise InputError("v0 requires 2--4 fixed shards")
    req = prepare(raw)
    if not 2 <= req.env.n <= 4:
        raise InputError("v0 accepts only 2--4 carrier positions")
    domain = saturate(req.env, req.selected, req.budget)
    rows = [{"state_id": i, "causal": {name: typed_wire(value) for name, value in leaves(state).items()},
             "word": domain.word(domain.representatives[i]),
             "successors": {letter: domain.successors[i, letter] for letter in ("p", "d")}}
            for i, state in enumerate(domain.summaries)]
    program = {"q": ir(req.q), "reports": [{"label": name, "expr": ir(expr)} for name, expr in req.reports],
               "commands": [{"label": c.label, "letter": c.letter, "guard": ir(c.guard)} for c in req.commands]}
    env = {"defect": list(req.env.defect), "ports": list(req.env.ports), "atom_count": len(req.env.atoms)}
    closure = source_closure()
    binding = {"versions": VERSIONS, "request_sha256": req.sha256, "domain_sha256": sha(rows),
               "program_sha256": sha(program), "environment_sha256": sha(env), "closure_sha256": sha(closure)}
    plan = {"schema": SCHEMA, "binding": binding, "raw_request": raw, "environment": env,
            "program": program, "states": rows, "log_state_count": len(domain.logs), "source_closure": closure,
            "shards": [{"shard_id": f"shard-{i:03d}", "members": list(range(i, len(rows), shards))}
                       for i in range(shards)]}
    plan["plan_id"] = sha(plan)
    return plan, req, domain


def prepare_plan(raw, shards=3):
    return _materialize(raw, shards)[0]


def task_for(plan, shard):
    payload = {"schema": SCHEMA + ".task", "binding": plan["binding"], "plan_id": plan["plan_id"],
               "shard_id": shard["shard_id"], "environment": plan["environment"], "program": plan["program"],
               "states": [{"state_id": i, "causal": plan["states"][i]["causal"]} for i in shard["members"]],
               "max_steps": plan["raw_request"].get("resources", {}).get("max_steps", 10_000_000)}
    return {"input": payload, "input_sha256": sha(payload)}


def _reference_signatures(req, domain):
    qs = [evaluate(req.q, leaves(state), req.env, req.budget) for state in domain.summaries]
    rows = []
    for i, state in enumerate(domain.summaries):
        query = leaves(state)
        reports = [{"label": name, "value": typed_wire(evaluate(expr, query, req.env, req.budget))}
                   for name, expr in req.reports]
        enabled = [c.label for c in req.commands if evaluate(c.guard, query, req.env, req.budget).data]
        successors = {c.label: typed_wire(qs[domain.successors[i, c.letter]])
                      for c in req.commands if c.label in enabled}
        rows.append((typed_wire(qs[i]), {"reports": reports, "enabled": enabled, "successor_q": successors}))
    return rows


def _local_conflicts(records):
    groups = {}
    for record in records:
        groups.setdefault(canonical(record["q_key"]), []).append(record["witness_state_id"])
    return [{"left": sorted(ids)[0], "right": sorted(ids)[1]} for _, ids in sorted(groups.items()) if len(ids) > 1]


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def _conflict(req, seen):
    fibers = {}
    for ident in sorted(seen):
        q, signature = seen[ident]
        fibers.setdefault(canonical(q), []).append((ident, signature))
    for kind, menu in (("R", [label for label, _ in req.reports]),
                       ("G", [c.label for c in req.commands]), ("T", [c.label for c in req.commands])):
        for column, label in enumerate(menu):
            for members in fibers.values():
                pivot, first = members[0]
                for other, second in members[1:]:
                    req.budget.tick()
                    if kind == "R":
                        differs = canonical(first["reports"][column]) != canonical(second["reports"][column])
                    elif kind == "G":
                        differs = (label in first["enabled"]) != (label in second["enabled"])
                    else:
                        differs = label in first["enabled"] and canonical(first["successor_q"][label]) != canonical(second["successor_q"][label])
                    if differs:
                        return {"kind": kind, "label": label}, pivot, other
    return None


def reduce_plan(raw, plan, results):
    base = {"schema": SCHEMA + ".decision", "status": "UNRESOLVED", "domain_complete": False,
            "coverage_complete": False, "canonical_compiler_admission": False,
            "worker_attestation_claimed": False, "reference_check": False}
    try:
        expected, req, domain = _materialize(raw, len(plan["shards"]))
        base.update(domain_complete=True, plan_id=expected["plan_id"], request_sha256=req.sha256,
                    domain={"log_states": len(domain.logs), "causal_states": len(domain.summaries)})
        _need(canonical(expected) == canonical(plan), "plan differs from exact regenerated domain/binding")
        _need(bool(domain.summaries), "empty registered domain is not a supplied invocation")
        _need(len(results) == len(plan["shards"]), "missing or duplicate shard result")
        by_id = {}
        for result in results:
            _need(result.get("status") == "COMPLETE", "worker incomplete, crashed or limited")
            ident = result["shard_id"]
            _need(ident not in by_id, "duplicate shard ID")
            by_id[ident] = result
        _need(set(by_id) == {s["shard_id"] for s in plan["shards"]}, "foreign/missing shard ID")
        reference = _reference_signatures(req, domain)
        seen = {}
        for shard in plan["shards"]:
            result, task = by_id[shard["shard_id"]], task_for(plan, shard)
            for key, value in (("schema", SCHEMA + ".shard"), ("binding", plan["binding"]),
                               ("plan_id", plan["plan_id"]), ("task_input_sha256", task["input_sha256"]),
                               ("coverage_digest", sha(shard["members"]))):
                _need(canonical(result.get(key)) == canonical(value), f"shard {key} binding mismatch")
            _need(type(result.get("evaluation_steps")) is int and
                  0 <= result["evaluation_steps"] <= task["input"]["max_steps"], "worker step accounting mismatch")
            covered, variants = set(), set()
            for record in result["fiber_records"]:
                _need(set(record) == {"q_key", "signature", "members", "witness_state_id"}, "fiber record shape")
                ids = record["members"]
                _need(type(ids) is list and ids and all(type(i) is int for i in ids), "invalid state IDs")
                _need(ids == sorted(set(ids)) and type(record["witness_state_id"]) is int and
                      record["witness_state_id"] == ids[0], "membership/representative mismatch")
                variant = canonical([record["q_key"], record["signature"]])
                _need(variant not in variants, "duplicate unaggregated signature")
                variants.add(variant)
                for ident in ids:
                    _need(ident in shard["members"] and ident not in covered and ident not in seen, "foreign/duplicate member")
                    _need(canonical(reference[ident]) == variant, "worker signature differs from reference")
                    covered.add(ident)
                    seen[ident] = (record["q_key"], record["signature"])
            _need(covered == set(shard["members"]), "shard state coverage incomplete")
            _need(canonical(result["local_conflicts"]) == canonical(_local_conflicts(result["fiber_records"])), "local conflict summary inconsistent")
        _need(set(seen) == set(range(len(domain.summaries))), "global coverage incomplete")
        base.update(coverage_complete=True, reference_check=True)
        conflict = _conflict(req, seen)
        q_states = len({canonical(q) for q, _ in seen.values()})
        base["q_states"] = q_states
        if conflict is None:
            return {**base, "status": "PASS", "q2_status": "PASS_EXACT", "checks": {"R": True, "G": True, "T": True}}
        clause, left, right = conflict
        status = {"R": "FAIL_READ", "G": "FAIL_GUARD", "T": "FAIL_SUCCESSOR"}[clause["kind"]]
        witness = {"clause": clause}
        for name, ident in (("left", left), ("right", right)):
            word = domain.word(domain.representatives[ident])
            item = observation(req, domain.summaries[ident], word)
            if clause["kind"] == "T":
                command = next(c for c in req.commands if c.label == clause["label"])
                following = domain.successors[ident, command.letter]
                q = evaluate(req.q, leaves(domain.summaries[following]), req.env, req.budget)
                from ..q2.values import encode
                item["after"] = {"word": word + command.letter, "q": encode(q, req.env)}
            witness[name] = item
        rejection = {"request_sha256": req.sha256, "status": status, "witness": witness}
        replay = verify_rejection(raw, rejection)
        _need(replay["status"] == "VALID_REJECTION_WITNESS", "independent rejection replay failed")
        return {**base, "status": "FAIL", "q2_status": status, "rejection": rejection, "replay": replay}
    except (Exception, MemoryError) as error:
        return {**base, "status": "UNRESOLVED", "reason": type(error).__name__, "detail": str(error)}


def run_task(task, path, timeout=30):
    process = None
    try:
        path.write_bytes(canonical(task))
        process = subprocess.Popen([str(worker_binary()), str(path)], cwd=ROOT,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate(timeout=timeout)
        if process.returncode or stderr:
            try:
                worker_detail = load_json(stdout)
            except Exception:
                worker_detail = None
            return {"status": "UNRESOLVED", "reason": "WORKER_FAILURE", "returncode": process.returncode,
                    "stderr": stderr.decode(errors="replace")[:1000], "worker_detail": worker_detail}
        return load_json(stdout)
    except Exception as error:
        return {"status": "UNRESOLVED", "reason": type(error).__name__, "detail": str(error)}
    finally:
        if process is not None:
            if process.poll() is None:
                process.kill()
            process.communicate()


def execute(raw, shards=3, output=None, timeout=30):
    started = perf_counter()
    try:
        plan = prepare_plan(raw, shards)
    except (Exception, MemoryError) as error:
        return {"schema": SCHEMA + ".decision", "status": "UNRESOLVED", "domain_complete": False,
                "coverage_complete": False, "reason": type(error).__name__, "detail": str(error)}
    enumeration_seconds = perf_counter() - started
    temporary = tempfile.TemporaryDirectory() if output is None else None
    directory = Path(temporary.name) if temporary else Path(output)
    try:
        if temporary is None:
            directory.mkdir(parents=True, exist_ok=False)
        (directory / "request.json").write_bytes(canonical(raw))
        (directory / "plan.json").write_bytes(canonical(plan))
        tasks = [task_for(plan, shard) for shard in plan["shards"]]
        started = perf_counter()
        with ThreadPoolExecutor(max_workers=shards) as pool:
            futures = [pool.submit(run_task, task, directory / f"{shard['shard_id']}.input.json", timeout)
                       for task, shard in zip(tasks, plan["shards"])]
            results = [future.result() for future in futures]
        worker_seconds = perf_counter() - started
        for shard, result in zip(plan["shards"], results):
            (directory / f"{shard['shard_id']}.output.json").write_bytes(canonical(result))
        started = perf_counter()
        decision = reduce_plan(raw, plan, results)
        if source_closure() != plan["source_closure"]:
            decision = {"status": "UNRESOLVED", "reason": "SOURCE_CLOSURE_CHANGED"}
        reduction_seconds = perf_counter() - started
        (directory / "decision.json").write_bytes(canonical(decision))
        receipt = {"schema": SCHEMA + ".receipt", "plan_id": plan["plan_id"], "decision": decision["status"],
                   "source_closure": plan["source_closure"], "files": {p.name: file_sha(p) for p in sorted(directory.glob("*.json"))},
                   "timings": {"enumeration_seconds": enumeration_seconds, "parallel_worker_wall_seconds": worker_seconds,
                               "reducer_reference_wall_seconds": reduction_seconds}, "performance_claim": False,
                   "public_release_claimed": False, "receipt_self_bound": False}
        (directory / "receipt.json").write_bytes(canonical(receipt))
        return decision
    except (Exception, MemoryError) as error:
        return {"schema": SCHEMA + ".decision", "status": "UNRESOLVED", "domain_complete": True,
                "coverage_complete": False, "receipt_written": False,
                "reason": type(error).__name__, "detail": str(error)}
    finally:
        if temporary:
            temporary.cleanup()


def verify_run(directory):
    """Check the closed file set, then rerun the trusted reducer without workers."""
    try:
        directory = Path(directory).resolve(strict=True)
        def read(name):
            path = directory / name
            _need(path.is_file() and not path.is_symlink() and path.resolve().parent == directory,
                  "receipt member is not a confined regular file")
            return load_json(path.read_bytes())
        raw, plan, receipt = read("request.json"), read("plan.json"), read("receipt.json")
        expected = prepare_plan(raw, len(plan["shards"]))
        _need(canonical(plan) == canonical(expected), "receipt plan/domain binding mismatch")
        names = {"request.json", "plan.json", "decision.json"}
        names |= {f"{shard['shard_id']}.{suffix}.json" for shard in plan["shards"] for suffix in ("input", "output")}
        _need({path.name for path in directory.iterdir()} == names | {"receipt.json"}, "receipt inventory mismatch")
        _need(set(receipt["files"]) == names, "receipt file closure mismatch")
        for name in names:
            read(name)
            _need(file_sha(directory/name) == receipt["files"][name], "receipt file digest mismatch")
        _need(receipt["schema"] == SCHEMA + ".receipt" and receipt["plan_id"] == plan["plan_id"], "receipt schema/plan mismatch")
        _need(canonical(receipt["source_closure"]) == canonical(source_closure()), "receipt implementation drift")
        _need(receipt["performance_claim"] is False and receipt["public_release_claimed"] is False and
              receipt["receipt_self_bound"] is False, "receipt claim boundary mismatch")
        results = []
        for shard in plan["shards"]:
            _need(canonical(read(f"{shard['shard_id']}.input.json")) == canonical(task_for(plan,shard)), "saved task mismatch")
            results.append(read(f"{shard['shard_id']}.output.json"))
        decision = reduce_plan(raw, plan, results)
        _need(canonical(read("decision.json")) == canonical(decision) and receipt["decision"] == decision["status"], "saved decision mismatch")
        return {"status":"VERIFIED_LOCAL_CLOSURE", "decision":decision["status"], "plan_id":plan["plan_id"],
                "coverage_complete":decision.get("coverage_complete",False), "independent_validation":False,
                "canonical_compiler_admission":False}
    except (Exception, MemoryError) as error:
        return {"status":"UNRESOLVED", "reason":type(error).__name__, "detail":str(error)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", nargs="?", type=Path)
    parser.add_argument("--shards", type=int, default=3)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--verify-run", type=Path)
    parser.add_argument("--worker-timeout", type=float, default=30)
    args = parser.parse_args()
    try:
        if args.verify_run:
            result = verify_run(args.verify_run)
        else:
            if args.request is None or args.output_dir is None:
                raise InputError("request and --output-dir required")
            build_worker()
            raw = load_json(args.request.read_bytes())
            result = execute(raw, args.shards, args.output_dir, args.worker_timeout)
    except Exception as error:
        result = {"status": "UNRESOLVED", "reason": type(error).__name__, "detail": str(error)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result["status"] == "UNRESOLVED" or result.get("decision") == "UNRESOLVED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
