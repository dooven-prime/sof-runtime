"""Read-only use of the unchanged application probe; never execute/rebuild."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

from applications.malecns_profile_census.protocol import canonical_bytes, sha256_file
from .fixtures import digest

ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT/"plugins/rust/cache-cost-probe/target/release/cache-cost-probe.exe"
CACHE = ROOT/"plugins/rust/prepared-input-cache/target/release/prepared-input-cache.exe"
REQUEST = ROOT/"runs/malecns-profile-census/packet-fusion-v1/request.json"
ORIGIN = ROOT/"runs/malecns-profile-census/cache-baseline-v1-final"
RECEIPT = ROOT/"applications/malecns_profile_census/results/prepared-cache.v1/cache-benchmark.v1.json"


def bindings():
    receipt = json.loads(RECEIPT.read_bytes()); result = {}
    for name, expected in receipt["implementation_sha256"].items():
        if name.startswith(("applications/", "plugins/", "tests/")):
            actual = sha256_file(ROOT/name)
            if actual != expected: raise ValueError("old cache closure changed: "+name)
            result[name] = actual
    for p, expected in ((CACHE, receipt["implementation_sha256"]["cache_binary"]),
                        (ROOT/"plugins/rust/malecns-profile-census/target/release/malecns-profile-census.exe",
                         receipt["implementation_sha256"]["census_binary"])):
        if sha256_file(p) != expected: raise ValueError("old producer/consumer binary drift")
        result[p.relative_to(ROOT).as_posix()] = expected
    cost = ROOT/"applications/malecns_profile_census/results/cache-cost.v1/cost-decomposition.v1.json"
    for name, expected in json.loads(cost.read_bytes())["implementation_sha256"].items():
        p = PROBE if name == "probe_binary" else Path(sys.executable) if name == "python_executable" else ROOT/name
        if sha256_file(p) != expected: raise ValueError("original probe closure changed: "+name)
    for p in (RECEIPT, REQUEST, PROBE, cost, ROOT/"plugins/rust/cache-cost-probe/src/main.rs",
              ROOT/"plugins/rust/cache-cost-probe/Cargo.toml", ROOT/"plugins/rust/cache-cost-probe/Cargo.lock",
              ROOT/"applications/malecns_profile_census/results/full-carrier-somaside.v1/semantic-result.json"):
        result[p.relative_to(ROOT).as_posix()] = sha256_file(p)
    return result


def source_request():
    request = json.loads(REQUEST.read_bytes())
    receipt = json.loads(RECEIPT.read_bytes())
    key = digest(request["identity"])
    if key != receipt["identity_key"]: raise ValueError("archived identity/key mismatch")
    return request, ORIGIN/"cache/entries"/key


def source_files():
    request, _ = source_request(); result = {}
    for declared in request["identity"]["sources"]:
        p = Path(request["source_paths"][declared["role"]])
        actual = {"size": p.stat().st_size, "sha256": sha256_file(p)}
        if any(actual[k] != declared[k] for k in actual): raise ValueError("original source changed")
        result[declared["role"]] = actual
    return result


def probe(request, cache_root, output):
    """The existing probe calls verify_sources + validate_entry, with no writes."""
    request = deepcopy(request); request["cache_root"] = str(Path(cache_root).resolve())
    request["invalid_policy"] = "reject"; request["consumer"] = None
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    envelope = {"schema": "sof-runtime.cache-cost-probe.v1", "id": 0, "action": "probe", "request": request}
    path = output/"probe-request.json"; path.write_bytes(canonical_bytes(envelope))
    done = subprocess.run([str(PROBE), "--once", str(path)], cwd=ROOT, capture_output=True, timeout=120)
    (output/"stdout.json").write_bytes(done.stdout); (output/"stderr.txt").write_bytes(done.stderr)
    if done.returncode or done.stderr: raise ValueError("old read-only probe failed to complete")
    value = json.loads(done.stdout)
    if value.get("id") != 0 or value.get("schema") != envelope["schema"]: raise ValueError("probe protocol")
    return {"result": value["result"], "probe_executable_sha256": sha256_file(PROBE),
            "request_sha256": sha256_file(path), "returncode": done.returncode,
            "application_cache_lookup_invoked": False, "consumer_executed": False}
