"""Second application shadow, with original packet/cache policy left intact."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

from applications.malecns_profile_census.protocol import canonical_bytes, sha256_file
from applications.solana_inventory_shadow.evidence import inventory
from applications.solana_source_advancement.runner import tree_hashes
from . import original
from .fixtures import controls, copy_flat, declarations, tiny, invalidate_record, rebind_packet_digest
from .reference import decode, encode
from .runner import ROOT, HERE, CRATE, binary, build, bindings, invoke, compare


def prior_a0(plan):
    receipt = ROOT/plan["prior_solana_receipt"]
    if sha256_file(receipt) != plan["prior_solana_receipt_sha256"]: raise ValueError("prior receipt changed")
    r = json.loads(receipt.read_bytes()); saved = ROOT/plan["prior_a0_snapshot"]
    expected = r["implementation_sha256"]["shadow"]
    for p in [saved/"Cargo.toml", saved/"Cargo.lock", *sorted((saved/"src").glob("*.rs"))]:
        key = "plugins/rust/a0-inventory-inspector/"+p.relative_to(saved).as_posix()
        if sha256_file(p) != expected[key]: raise ValueError("prior A0 source snapshot changed")
    if sha256_file(saved/"a0-inventory-inspector.exe") != plan["prior_a0_binary_sha256"]: raise ValueError("prior observer bytes changed")
    return {"receipt_sha256": sha256_file(receipt), "snapshot": tree_hashes(saved)}


def command(root, name, argv, timeout=180):
    env = dict(os.environ); env.pop("PYTHONOPTIMIZE", None)
    with (root/(name+".stdout.txt")).open("xb") as out, (root/(name+".stderr.txt")).open("xb") as err:
        subprocess.run(argv, cwd=ROOT, env=env, stdout=out, stderr=err, check=True, timeout=timeout)


def run(directory):
    build(); root = Path(directory).resolve(); root.mkdir(parents=True, exist_ok=False)
    plan = json.loads((HERE/"plan.v0.json").read_bytes()); before = bindings(); historical = prior_a0(plan)
    origin = ROOT/plan["origin_run"]
    if sha256_file(origin/"cache-benchmark.v1.json") != plan["origin_receipt_sha256"]: raise ValueError("origin receipt identity")
    old_files = tree_hashes(origin); sources = original.source_files(); request, source = original.source_request()
    decl = declarations(request, sha256_file(original.CACHE))
    if decl["producer"]["executable_sha256"] == sha256_file(binary()): raise ValueError("observer replaced producer identity")
    # Existing Solana controls get a new source-bound run, never a new identity
    # attributed to their old receipt or executable.
    command(root, "solana-regression", [sys.executable, "-B", "-m", "applications.solana_inventory_shadow.acceptance", str(root/"solana-regression")])
    from applications.solana_inventory_shadow.verify import verify as verify_solana
    cross = verify_solana(root/"solana-regression")
    for optimized in (False, True):
        command(root, "cache-tests"+("-O" if optimized else ""), [sys.executable, "-B"]+(["-O"] if optimized else [])+
                ["-m", "unittest", "discover", "-s", "tests/cross_language", "-p", "test_a0_malecns_cache_shadow.py", "-v"])
    cases = []

    def row(name, data, m, b, expected, kind="static"):
        o = invoke(data, m, b, root/"logs", name); ref = compare(data, m, b, o)
        if o["status"] != expected: raise ValueError(f"unexpected {name}: {o}")
        value = {"name": name, "kind": kind, "data": str(data.relative_to(root)), "manifest": str(m.relative_to(root)),
                 "bindings": str(b.relative_to(root)), "observation": o, "python_reference": ref}
        cases.append(value); return value

    entry = copy_flat(source, root/"cases/cache-entry/cache/entries"/source.name)
    m, b = controls(entry, root/"cases/cache-entry/controls", decl)
    normal = row("normal-cache-entry", entry, m, b, "MATCHED_BYTES", "normal")
    initial = tree_hashes(entry)
    normal["original_files"] = initial
    normal["original_application"] = original.probe(request, entry.parent.parent, root/"normal-probe")
    if normal["original_application"]["result"]["status"] != "PROBED_NOT_CONSUMED": raise ValueError("old normal validation")
    archive = root/"cases/archive/data"; archive.mkdir(parents=True)
    archive_sources = {"cache-benchmark.v1.json": origin/"cache-benchmark.v1.json", "request.json": original.REQUEST,
                       "semantic-result.json": ROOT/"applications/malecns_profile_census/results/full-carrier-somaside.v1/semantic-result.json"}
    for name, p in archive_sources.items(): shutil.copyfile(p, archive/name)
    am, ab = controls(archive, root/"cases/archive/controls", decl)
    row("normal-archive", archive, am, ab, "MATCHED_BYTES", "normal")["original_files"] = tree_hashes(archive)

    for kind in plan["declaration_controls"]:
        folder = root/"cases"/("decl-"+kind); data, cm, cb = tiny(folder)
        value, expected = decode(cm.read_bytes()), decode(cb.read_bytes())
        if kind.endswith("-role"):
            name = kind.removesuffix("-role")
            for v in (value, expected): v["declarations"]["identities"][name]["role"] = "CheckpointIdentity"
        elif kind == "checkpoint-slot":
            for v in (value, expected):
                ids = v["declarations"]["identities"]; ids["checkpoint"] = ids.pop("cache"); ids["checkpoint"]["role"] = "CheckpointIdentity"
        elif kind == "wrong-cache-key": value["declarations"]["identities"]["cache"]["sha256"] = "1"*64
        elif kind == "wrong-producer": value["declarations"]["producer"]["executable_sha256"] = sha256_file(binary())
        elif kind == "profile": value["schema"] = "sof-runtime.a0-flat-inventory.v0"
        cm.write_bytes(encode(value)); cb.write_bytes(encode(expected))
        if kind == "control-in-root": target = data/"inventory.json"; shutil.copyfile(cm, target); cm = target
        row("decl-"+kind, data, cm, cb, "REJECTED", "declaration")

    for kind in plan["file_controls"]:
        folder = root/"cases"/("file-"+kind); data, cm, cb = tiny(folder); p = data/"packet.bin"
        if kind == "missing": p.unlink()
        elif kind == "extra": (data/"extra.bin").write_bytes(b"extra")
        elif kind == "damaged": p.write_bytes(b"X"+p.read_bytes()[1:])
        elif kind == "truncated": p.write_bytes(p.read_bytes()[:-1])
        elif kind == "wrong-type": p.unlink(); p.mkdir()
        elif kind == "actual-case": p.rename(data/"PACKET.BIN")
        elif kind == "hardlink": p.rename(folder/"retained.bin"); os.link(folder/"retained.bin", p)
        elif kind == "file-ads":
            with open(str(p)+":hidden", "wb") as stream: stream.write(b"stream")
        row("file-"+kind, data, cm, cb, "REJECTED", "filesystem")

    for point in plan["kill_points"]:
        name = "kill-"+point; o = invoke(entry, m, b, root/"logs", name, pause=point)
        if o["status"] != "INCOMPLETE" or not o["process"]["actually_killed"]: raise ValueError("kill admitted")
        fresh = invoke(entry, m, b, root/"logs", name+"-fresh"); compare(entry, m, b, fresh)
        if fresh["status"] != "MATCHED_BYTES": raise ValueError("fresh kill check")
        cases.append({"name": name, "kind": "kill", "data": str(entry.relative_to(root)), "manifest": str(m.relative_to(root)),
                      "bindings": str(b.relative_to(root)), "observation": o, "fresh": fresh, "fault_point": point})

    for kind in plan["mutation_controls"]:
        folder = root/"cases"/("mutation-"+kind); data, cm, cb = tiny(folder); p = data/"packet.bin"
        def change():
            if kind == "content": p.write_bytes(b"X"+p.read_bytes()[1:])
            elif kind == "replacement": p.rename(folder/"retired.bin"); shutil.copyfile(folder/"retired.bin", p)
            elif kind == "extra-file": (data/"extra.bin").write_bytes(b"extra")
            else:
                with open(str(p)+":hidden", "wb") as stream: stream.write(b"stream")
        name = "mutation-"+kind; o = invoke(data, cm, cb, root/"logs", name, pause="after_hash", change=change)
        if o["status"] != "INCOMPLETE" or o["result"]["error"]["code"] != "INPUT_CHANGED": raise ValueError("changed interval admitted")
        fresh = invoke(data, cm, cb, root/"logs", name+"-fresh"); compare(data, cm, cb, fresh)
        if fresh["status"] != ("MATCHED_BYTES" if kind == "replacement" else "REJECTED"): raise ValueError("fresh mutation check")
        cases.append({"name": name, "kind": "mutation", "data": str(data.relative_to(root)), "manifest": str(cm.relative_to(root)),
                      "bindings": str(cb.relative_to(root)), "observation": o, "fresh": fresh})

    folder = root/"cases/expired-observation"; data, cm, cb = tiny(folder)
    first = invoke(data, cm, cb, root/"logs", "interval-first"); compare(data, cm, cb, first)
    old_view = copy_flat(data, folder/"before-view"); p = data/"packet.bin"; p.write_bytes(b"X"+p.read_bytes()[1:])
    later = invoke(data, cm, cb, root/"logs", "interval-later"); compare(data, cm, cb, later)
    if first["status"] != "MATCHED_BYTES" or later["status"] != "REJECTED": raise ValueError("future credential")
    cases.append({"name": "expired-observation", "kind": "expiry", "data": str(data.relative_to(root)), "manifest": str(cm.relative_to(root)),
                  "bindings": str(cb.relative_to(root)), "observation": first, "later": later, "before_view": str(old_view.relative_to(root))})

    bad = copy_flat(source, root/"cases/semantic-boundary/cache/entries"/source.name)
    invalidate_record(bad/"packet.bin"); rebind_packet_digest(bad)
    bm, bb = controls(bad, root/"cases/semantic-boundary/controls", decl)
    boundary = row("semantic-boundary", bad, bm, bb, "MATCHED_BYTES", "semantic-boundary")
    boundary["original_application"] = original.probe(request, bad.parent.parent, root/"negative-probe")
    if boundary["original_application"]["result"] != {"status": "PROBE_REJECTED", "detail": "source record bounds/order"}:
        raise ValueError("not the original grammar rejection")
    if tree_hashes(entry) != initial or tree_hashes(origin) != old_files or before != bindings() or historical != prior_a0(plan) or sources != original.source_files():
        raise ValueError("original artifacts, identities or source bindings changed")
    for name in initial:
        if (entry/name).read_bytes() != (source/name).read_bytes(): raise ValueError("normal copy changed bytes")
    for name, p in archive_sources.items():
        if (archive/name).read_bytes() != p.read_bytes(): raise ValueError("archive copy changed bytes")
    record = {"schema": "sof-runtime.a0-malecns-cache-shadow-acceptance.v0", "status": "PASS_LOCAL_READ_ONLY_A0_CACHE_SHADOW",
              "created_utc": datetime.now(timezone.utc).isoformat(), "environment": {"platform": platform.platform(), "python": sys.version},
              "plan": plan, "implementation_sha256": before, "origin_files": old_files, "source_files": sources, "prior_a0_preserved": historical,
              "solana_regression": {"verification": cross, "receipt_sha256": sha256_file(root/"solana-regression/acceptance.v0.json")},
              "cases": cases, "controls": {"real_kills": 3, "changed_intervals": 4, "original_artifacts_unchanged": True,
                  "normal_and_optimized_tests": "PASS", "semantic_integrity_separation": "PASS", "cache_hit_permission": "NOT_GRANTED",
                  "public_api": False, "b_or_c_extracted": False, "cache_path_migrated": False, "a_library_extraction_approved": False},
              "files": inventory(root, exclude=("acceptance.v0.json",))}
    (root/"acceptance.v0.json").write_bytes(canonical_bytes(record)); return record


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__); p.add_argument("directory", type=Path)
    r = run(p.parse_args().directory); print(json.dumps({"status": r["status"], "cases": len(r["cases"]), "controls": r["controls"]}, sort_keys=True))
