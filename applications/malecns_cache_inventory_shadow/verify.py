"""Verify saved byte closure and Python decisions, not past process execution."""
import argparse
import json
from pathlib import Path

from applications.malecns_profile_census.protocol import sha256_file, read_header, iter_records
from applications.solana_inventory_shadow.evidence import inventory
from applications.solana_inventory_shadow.verify import verify as verify_solana
from applications.solana_source_advancement.runner import tree_hashes
from .acceptance import prior_a0
from . import original
from .fixtures import declarations
from .reference import Handle, decode
from .runner import ROOT, HERE, binary, bindings, compare


def verify(directory):
    root = Path(directory).resolve(strict=True); receipt = root/"acceptance.v0.json"
    h = Handle(receipt)
    try: h.stamp()
    finally: h.close()
    r = json.loads(receipt.read_bytes()); plan = json.loads((HERE/"plan.v0.json").read_bytes())
    if r["schema"] != "sof-runtime.a0-malecns-cache-shadow-acceptance.v0" or r["status"] != "PASS_LOCAL_READ_ONLY_A0_CACHE_SHADOW" or r["plan"] != plan:
        raise ValueError("acceptance identity")
    if r["implementation_sha256"] != bindings(): raise ValueError("implementation drift")
    if r["files"] != inventory(root, exclude=("acceptance.v0.json",)): raise ValueError("evidence type/bytes/streams changed")
    if r["origin_files"] != tree_hashes(ROOT/plan["origin_run"]) or r["source_files"] != original.source_files(): raise ValueError("old application/source data changed")
    if sha256_file(ROOT/plan["origin_run"]/"cache-benchmark.v1.json") != plan["origin_receipt_sha256"]: raise ValueError("old receipt changed")
    if r["prior_a0_preserved"] != prior_a0(plan): raise ValueError("previous observer/receipt not preserved")
    if r["solana_regression"]["receipt_sha256"] != sha256_file(root/"solana-regression/acceptance.v0.json") or r["solana_regression"]["verification"] != verify_solana(root/"solana-regression"):
        raise ValueError("two-profile Solana regression changed")
    required = {"normal-"+s for s in plan["normal_roots"]} | {"decl-"+s for s in plan["declaration_controls"]} | {"file-"+s for s in plan["file_controls"]}
    required |= {"kill-"+p for p in plan["kill_points"]} | {"mutation-"+s for s in plan["mutation_controls"]} | {"expired-observation", "semantic-boundary"}
    if len(r["cases"]) != len(required) or {c["name"] for c in r["cases"]} != required: raise ValueError("case coverage")

    def confined(name):
        p = Path(name)
        if p.is_absolute() or ".." in p.parts: raise ValueError("path escaped evidence root")
        return root/p

    def observation(o):
        name = o["observation_file"]; stem = name.removesuffix(".observation.json")
        if name != Path(name).name: raise ValueError("observation path")
        if json.loads((root/"logs"/name).read_bytes()) != o: raise ValueError("observation changed")
        if o["cache_hit_permission"] != "NOT_GRANTED" or o["cache_policy"] != "NOT_INVOKED" or o["application_decision"] != "NOT_ASSESSED":
            raise ValueError("application permission leaked into shadow")
        if o["schema"] != "sof-runtime.malecns-cache-inventory-shadow.observation.v0" or o["observer_executable_sha256"] != sha256_file(binary()): raise ValueError("observer identity")
        for suffix, field in (("stdout.json", "stdout_sha256"), ("stderr.txt", "stderr_sha256")):
            if sha256_file(root/"logs"/(stem+"."+suffix)) != o["process"][field]: raise ValueError("output bytes changed")
        if o["process"]["actually_killed"]:
            if o["status"] != "INCOMPLETE" or o["result"] is not None: raise ValueError("partial output admitted")
            if json.loads((root/"logs"/(stem+".marker.json")).read_bytes()) != o["process"]["marker"]: raise ValueError("actual kill marker changed")
        elif json.loads((root/"logs"/(stem+".stdout.json")).read_bytes()) != o["result"]: raise ValueError("Rust result record")
        if o["matching_observation_admissible"] != (o["status"] == "MATCHED_BYTES"): raise ValueError("mechanical admission")
        if o["status"] == "MATCHED_BYTES":
            v = o["result"]
            if o["process"]["returncode"] != 0 or v["observer_identity"] != {"role": "ShadowObserverExecution", "sha256": sha256_file(binary())} or v["validity"] != "OBSERVED_INTERVAL_ONLY" or v["source_trust"] != "NOT_ASSESSED" or v["application_decision"] != "NOT_ASSESSED":
                raise ValueError("semantic/lifetime boundary")

    request, source = original.source_request()
    archive_sources = {"cache-benchmark.v1.json": original.ORIGIN/"cache-benchmark.v1.json", "request.json": original.REQUEST,
                       "semantic-result.json": ROOT/"applications/malecns_profile_census/results/full-carrier-somaside.v1/semantic-result.json"}
    for row in r["cases"]:
        data, m, b = (confined(row[k]) for k in ("data", "manifest", "bindings")); o = row["observation"]; observation(o)
        if row["kind"] == "kill":
            if not o["process"]["actually_killed"] or o["process"]["marker"]["point"] != row["fault_point"]: raise ValueError("kill coverage")
            observation(row["fresh"]); compare(data, m, b, row["fresh"])
            if row["fresh"]["status"] != "MATCHED_BYTES": raise ValueError("fresh kill observation")
        elif row["kind"] == "mutation":
            if not o["process"]["changed_during_observation"] or o["status"] != "INCOMPLETE" or o["result"]["error"]["code"] != "INPUT_CHANGED": raise ValueError("mutation admitted")
            observation(row["fresh"]); compare(data, m, b, row["fresh"])
        elif row["kind"] == "expiry":
            compare(confined(row["before_view"]), m, b, o)
            observation(row["later"]); compare(data, m, b, row["later"])
            if o["status"] != "MATCHED_BYTES" or row["later"]["status"] != "REJECTED": raise ValueError("observation reused")
        else:
            compare(data, m, b, o)
            if row["kind"] in ("filesystem", "declaration") and o["status"] != "REJECTED": raise ValueError("negative control")
        if row["kind"] == "normal":
            originals = {p.name: p for p in source.iterdir()} if row["name"] == "normal-cache-entry" else archive_sources
            if tree_hashes(data) != row["original_files"]: raise ValueError("normal copy digest")
            for name, p in originals.items():
                if (data/name).read_bytes() != p.read_bytes(): raise ValueError("normal copy not byte-identical")
            if decode(m.read_bytes())["declarations"] != declarations(request, sha256_file(original.CACHE)): raise ValueError("application identity derivation")
        if row["kind"] == "semantic-boundary":
            if o["status"] != "MATCHED_BYTES" or row["original_application"]["result"] != {"status": "PROBE_REJECTED", "detail": "source record bounds/order"}: raise ValueError("missing semantic distinction")
            cm = json.loads((data/"manifest.json").read_bytes())
            if cm["packet"]["sha256"] != sha256_file(data/"packet.bin") or cm["identity"] != request["identity"]: raise ValueError("negative manifest not truthful")
            with (data/"packet.bin").open("rb") as stream:
                header = read_header(stream)
                if header != request["identity"]["expected_header"]: raise ValueError("negative header changed")
                try: next(iter_records(stream, header))
                except ValueError as e:
                    if str(e) != "invalid source record": raise
                else: raise ValueError("Python application grammar did not reject")
        if "original_application" in row:
            name = "negative-probe" if row["kind"] == "semantic-boundary" else "normal-probe"
            saved = json.loads((root/name/"stdout.json").read_bytes())
            if saved["result"] != row["original_application"]["result"] or row["original_application"]["probe_executable_sha256"] != sha256_file(original.PROBE): raise ValueError("original probe output")
            if row["original_application"]["application_cache_lookup_invoked"] or row["original_application"]["consumer_executed"]: raise ValueError("cache execution was invoked")
    return {"status": "VERIFIED_LOCAL_SAVED_A0_CACHE_SHADOW", "cases": len(r["cases"]), "real_kills": 3,
            "rust_reexecuted": False, "independent_execution_attestation": False, "cache_hit_permission": "NOT_GRANTED",
            "cache_path_migrated": False, "b_or_c_extracted": False, "a_library_extraction_approved": False}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__); p.add_argument("directory", type=Path)
    print(json.dumps(verify(p.parse_args().directory), sort_keys=True))
