"""One original Solana producer, exact artifact copies, and read-only A0 controls."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

from applications.solana_offchain_slice.common import canonical, parse, file_sha
from applications.solana_source_advancement.runner import tree_hashes
from applications.solana_source_advancement.reference import check_success
from applications.solana_publication_recovery.reference import check as original_check, predict as original_predict
from applications.solana_publication_recovery.runner import control as original_control, binary as original_binary
from .fixtures import controls, copy_flat, state_declarations
from .reference import encode, decode, inspect, Handle
from .runner import ROOT, HERE, CRATE, CORE, binary, build, bindings, invoke, compare
from .evidence import inventory


def run(directory):
    build(); root = Path(directory).resolve(); root.mkdir(parents=True, exist_ok=False)
    plan = parse((HERE/"plan.v0.json").read_bytes()); before = bindings()
    origin = ROOT/plan["origin_run"]; receipt_path = origin/"acceptance.v0.json"
    if file_sha(receipt_path) != plan["origin_receipt_sha256"]: raise ValueError("frozen producer receipt mismatch")
    prior = parse(receipt_path.read_bytes()); source_case = next(c for c in prior["cases"] if c["name"] == plan["origin_case"])
    source = origin/source_case["destination"]; source_req = origin/source_case["request"]
    producer_receipt = original_control(source)/"receipt.json"
    original_check(source_req, source, source_case["result"])
    original_files = tree_hashes(origin)
    # Check the actual original objects before copying; do not strip an
    # unsupported stream/link from a source and then call the copy faithful.
    for p in list(source.iterdir())+[producer_receipt]:
        h = Handle(p)
        try: h.ntfs(); h.stamp()
        finally: h.close()
    declared = state_declarations(source)
    if declared["producer"]["executable_sha256"] != file_sha(original_binary()) or file_sha(original_binary()) == file_sha(binary()):
        raise ValueError("producer and shadow identities were not kept distinct")
    for optimized in (False, True):
        name = "tests-optimized" if optimized else "tests"
        env = dict(os.environ); env.pop("PYTHONOPTIMIZE", None)
        args = [sys.executable, "-B"]+(["-O"] if optimized else [])+["-m", "unittest", "discover", "-s", "tests/cross_language", "-p", "test_a0_inventory_shadow.py", "-v"]
        with (root/f"{name}.stdout.txt").open("xb") as out, (root/f"{name}.stderr.txt").open("xb") as err:
            subprocess.run(args, cwd=ROOT, env=env, stdout=out, stderr=err, check=True, timeout=120)
    for args, label in ((["cargo", "test", "--locked", "--offline", "--manifest-path", str(CRATE/"Cargo.toml")], "rust-tests"),
                        (["cargo", "fmt", "--check", "--manifest-path", str(CRATE/"Cargo.toml")], "rust-format"),
                        (["cargo", "test", "--locked", "--offline", "--manifest-path", str(CORE/"Cargo.toml")], "core-tests"),
                        (["cargo", "fmt", "--check", "--manifest-path", str(CORE/"Cargo.toml")], "core-format")):
        with (root/f"{label}.stdout.txt").open("xb") as out, (root/f"{label}.stderr.txt").open("xb") as err:
            subprocess.run(args, cwd=ROOT, stdout=out, stderr=err, check=True, timeout=120)
    (root/"cases").mkdir(); cases = []; normal = {}

    def case(name, data, m, b, expected, **extra):
        observed = invoke(data, m, b, root/"logs", name)
        reference = compare(data, m, b, observed)
        if observed["status"] != expected: raise ValueError(f"wrong shadow outcome {name}: {observed}")
        row = {"name": name, "kind": extra.pop("kind", "static"), "data": str(Path(data).relative_to(root)),
               "manifest": str(Path(m).relative_to(root)), "bindings": str(Path(b).relative_to(root)),
               "observation": observed, "python_reference": reference, **extra}
        cases.append(row); return row

    for kind in plan["normal_roots"]:
        data = root/"cases"/kind/"data"
        if kind == "state": copy_flat(source, data)
        else: data.mkdir(parents=True); shutil.copyfile(producer_receipt, data/"receipt.json")
        m, b = controls(data, data.parent/"controls", declared)
        before_copy = tree_hashes(data)
        row = case("normal-"+kind, data, m, b, "MATCHED_BYTES", kind="normal")
        if tree_hashes(data) != before_copy: raise ValueError("read-only inspection changed copied bytes")
        normal[kind] = (data, m, b); row["original_files"] = before_copy

    state, template_m, template_b = normal["state"]
    for kind in plan["declaration_controls"]:
        name = "decl-"+kind; folder = root/"cases"/name
        data = copy_flat(state, folder/"data") if kind.startswith("control-in-root") else state
        m, b = controls(data, folder/"controls", declared); value = decode(m.read_bytes())
        first = dict(value["entries"][0])
        changes = {"device": "NUL.txt", "ads": "checkpoint.json:hidden", "traversal": "../checkpoint.json",
                   "drive": "C:checkpoint.json", "unc": "\\\\server\\checkpoint.json"}
        if kind in changes: value["entries"][0]["name"] = changes[kind]
        elif kind in ("case-alias", "duplicate"):
            if kind == "case-alias": first["name"] = first["name"].upper()
            value["entries"].append(first); value["entries"].sort(key=lambda x: x["name"])
        elif kind == "schema": value["declarations"]["schemas"][0]["id"] = "wrong-owner"
        elif kind == "producer": value["declarations"]["producer"]["executable_sha256"] = file_sha(binary())
        elif kind == "identity-role": value["declarations"]["identities"]["source"]["role"] = "ExecutionIdentity"
        elif kind == "version": value["codec"] = "unsupported.v999"
        elif kind == "unknown": value["extra-field"] = True
        elif kind == "unsorted": value["entries"].reverse()
        elif kind == "float": value["entries"][0]["byte_length"] = 1.0
        elif kind == "typed-metadata":
            value["declarations"]["producer"]["id"] = 7
            eb = decode(b.read_bytes()); eb["declarations"] = value["declarations"]; b.write_bytes(encode(eb))
        if kind == "float": m.write_bytes(canonical(value))
        else: m.write_bytes(encode(value))
        if kind == "noncanonical": m.write_bytes(m.read_bytes()+b"\n")
        if kind.startswith("control-in-root"):
            p = m if kind.endswith("manifest") else b; target = data/p.name; shutil.copyfile(p, target)
            if kind.endswith("manifest"): m = target
            else: b = target
        case(name, data, m, b, "REJECTED", kind="declaration")

    for kind in plan["file_controls"]:
        name = "file-"+kind; folder = root/"cases"/name; data = copy_flat(state, folder/"data")
        m, b = controls(data, folder/"controls", declared); p = next(data.glob("slot-*.jsonl"))
        if kind == "missing": p.unlink()
        elif kind == "extra": (data/"undeclared.bin").write_bytes(b"extra")
        elif kind == "damaged": p.write_bytes(b"X"+p.read_bytes()[1:])
        elif kind == "truncated": p.write_bytes(p.read_bytes()[:-1])
        elif kind == "wrong-type": p.unlink(); p.mkdir()
        elif kind == "actual-case": p.rename(data/p.name.upper())
        elif kind == "hardlink":
            target = folder/"same-bytes.bin"; target.write_bytes(p.read_bytes()); p.unlink(); os.link(target, p)
        elif kind in ("file-ads", "root-ads"):
            target = data if kind == "root-ads" else p
            with open(str(target)+":hidden", "wb") as stream: stream.write(b"undeclared stream")
        else:
            target = folder/"target"; target.mkdir(); (target/"retain.bin").write_bytes(b"retain")
            link = folder/"junction" if kind == "junction-root" else p
            if kind == "junction-entry": p.unlink()
            done = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW, timeout=10)
            if done.returncode: raise ValueError("mandatory real-junction control unavailable")
            if kind == "junction-root": data = link
        case(name, data, m, b, "REJECTED", kind="filesystem")

    for domain, (data, m, b) in normal.items():
        initial_copy = tree_hashes(data)
        for point in plan["kill_points"]:
            name = "kill-"+domain+"-"+point
            r = invoke(data, m, b, root/"logs", name, pause=point)
            if r["status"] != "INCOMPLETE" or not r["process"]["actually_killed"] or r["matching_observation_admissible"]:
                raise ValueError("killed/partial inspection admitted")
            fresh = invoke(data, m, b, root/"logs", name+"-fresh"); compare(data, m, b, fresh)
            if fresh["status"] != "MATCHED_BYTES" or tree_hashes(data) != initial_copy: raise ValueError("kill changed payload or fresh result")
            cases.append({"name": name, "kind": "kill", "data": str(data.relative_to(root)), "manifest": str(m.relative_to(root)),
                          "bindings": str(b.relative_to(root)), "observation": r, "fresh": fresh, "fault_point": point})

    for kind in plan["mutation_controls"]:
        name = "mutation-"+kind; folder = root/"cases"/name; data = copy_flat(state, folder/"data")
        m, b = controls(data, folder/"controls", declared); p = next(data.glob("slot-*.jsonl"))
        def change():
            if kind == "content": p.write_bytes(b"X"+p.read_bytes()[1:])
            elif kind == "replacement": raw = p.read_bytes(); p.rename(folder/"retired.jsonl"); p.write_bytes(raw)
            elif kind == "extra-file": (data/"extra.bin").write_bytes(b"extra")
            else:
                with open(str(p)+":hidden", "wb") as stream: stream.write(b"new stream")
        r = invoke(data, m, b, root/"logs", name, pause="after_hash", change=change)
        if r["status"] != "INCOMPLETE" or not r["process"]["changed_during_observation"] or r["result"]["error"]["code"] != "INPUT_CHANGED":
            raise ValueError("changed observation accepted")
        fresh = invoke(data, m, b, root/"logs", name+"-fresh"); reference = compare(data, m, b, fresh)
        if fresh["status"] != ("MATCHED_BYTES" if kind == "replacement" else "REJECTED"): raise ValueError("fresh observation mismatch")
        cases.append({"name": name, "kind": "mutation", "data": str(data.relative_to(root)), "manifest": str(m.relative_to(root)),
                      "bindings": str(b.relative_to(root)), "observation": r, "fresh": fresh, "python_fresh": reference})

    folder = root/"cases/expired-observation"; data = copy_flat(state, folder/"data")
    m, b = controls(data, folder/"controls", declared)
    first = invoke(data, m, b, root/"logs", "interval-first"); compare(data, m, b, first)
    preserved = copy_flat(data, folder/"before-view"); p = next(data.glob("slot-*.jsonl")); p.write_bytes(b"X"+p.read_bytes()[1:])
    later = invoke(data, m, b, root/"logs", "interval-later"); compare(data, m, b, later)
    if first["status"] != "MATCHED_BYTES" or later["status"] != "REJECTED": raise ValueError("observation treated as future credential")
    cases.append({"name": "expired-observation", "kind": "expiry", "data": str(data.relative_to(root)), "manifest": str(m.relative_to(root)),
                  "bindings": str(b.relative_to(root)), "observation": first, "later": later, "before_view": str(preserved.relative_to(root))})

    folder = root/"cases/semantic-boundary"; data = copy_flat(state, folder/"data"); p = next(data.glob("slot-*.jsonl"))
    rows = [parse(line) for line in p.read_bytes().splitlines()]; rows[1]["fee"] += 1
    p.write_bytes(b"".join(canonical(row)+b"\n" for row in rows))
    m, b = controls(data, folder/"controls", declared)
    boundary = case("semantic-boundary", data, m, b, "MATCHED_BYTES", kind="semantic-boundary")
    expected = original_predict(source_req, source)
    try: check_success(expected, source_case["result"]["advancement"], data)
    except ValueError as e: boundary["original_application_rejection"] = str(e)
    else: raise ValueError("A0 accidentally replaced application validation")

    for kind, (data, _, _) in normal.items():
        original_names = tree_hashes(source) if kind == "state" else {"receipt.json": file_sha(producer_receipt)}
        if tree_hashes(data) != original_names: raise ValueError("normal copy changed original artifact bytes")
        for name in original_names:
            original_path = source/name if kind == "state" else producer_receipt
            if (data/name).read_bytes() != original_path.read_bytes(): raise ValueError("copy not byte-identical")
    if tree_hashes(origin) != original_files or before != bindings(): raise ValueError("old producer closure or shadow code changed")
    record = {"schema": "sof-runtime.a0-solana-shadow-acceptance.v0", "status": "PASS_LOCAL_READ_ONLY_A0_SHADOW",
        "created_utc": datetime.now(timezone.utc).isoformat(), "plan": plan, "implementation_sha256": before,
        "environment": {"platform": platform.platform(), "python": sys.version},
        "origin": {"root_local": str(origin), "receipt_sha256": file_sha(receipt_path), "files": original_files,
                   "case": plan["origin_case"], "producer_executable_sha256": file_sha(original_binary()),
                   "producer_receipt_sha256": file_sha(producer_receipt), "semantic_reference": "UNCHANGED_READ_ONLY_PYTHON"},
        "cases": cases, "controls": {"ordinary_and_optimized_tests": "PASS", "rust_tests_and_compile_fail": "PASS",
            "full_manifest_bytes_and_entries": "PASS", "real_kills": 6, "changed_observation_rejected": 4,
            "original_artifacts_and_identity_unchanged": "PASS", "semantic_integrity_separation": "PASS",
            "b_or_c_extracted": False, "public_api": False, "independent_execution_attestation": False},
        "evidence_inventory_scope": {"exclude_exact_root_files": ["acceptance.v0.json"], "reparse_followed": False, "named_streams_bound": True},
        "files": inventory(root, exclude=("acceptance.v0.json",))}
    (root/"acceptance.v0.json").write_bytes(canonical(record))
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("directory", type=Path)
    args = parser.parse_args(); r = run(args.directory)
    print(canonical({"status": r["status"], "cases": len(r["cases"]), "controls": r["controls"]}).decode())
