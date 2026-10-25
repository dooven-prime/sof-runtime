"""Request factory and local caller for the Rust Prepared Input Cache v1."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
from time import perf_counter

from .prepare_input import PROXY_SIGN, PUBLISHED_CARRIER, fixture_data
from .protocol import SCHEMA, canonical_bytes, sha256_file
from .replay import ROOT, find_cargo, rust_binary


CRATE = ROOT / "plugins/rust/prepared-input-cache"
CONTRACT = ROOT / "applications/malecns_profile_census/PREPARED_INPUT_CACHE_V1.md"


class SourceIdentityError(ValueError):
    """A requested production source is outside the pinned carrier."""


def cache_binary() -> Path:
    return CRATE / "target/release" / ("prepared-input-cache.exe" if os.name == "nt" else "prepared-input-cache")


def build_cache() -> None:
    subprocess.run([find_cargo(), "build", "--release", "--locked", "--manifest-path", str(CRATE / "Cargo.toml")],
                   cwd=ROOT, check=True)


def cache_key(identity: dict) -> str:
    return hashlib.sha256(canonical_bytes(identity)).hexdigest()


def make_request(
    cache_root: Path, *, fixture: Path | None = None, edges: Path | None = None,
    nodes: Path | None = None, field: str = "somaSide", invalid_policy: str = "reject",
    execute: bool = False,
) -> dict:
    if invalid_policy not in ("reject", "rebuild"):
        raise ValueError("invalid cache policy")
    if fixture is not None:
        if edges is not None or nodes is not None:
            raise ValueError("fixture and carrier inputs are exclusive")
        fixture = fixture.resolve(strict=True)
        header, records = fixture_data(fixture)
        edge_count = sum(len(record["edges"]) for record in records)
        source_paths = {"CASE_FIXTURE": str(fixture)}
        command = ["-B", "-m", "applications.malecns_profile_census.prepare_input",
                   "--fixture", "{source:CASE_FIXTURE}", "--output", "{output}"]
        sign_mapping = {"fixture": "explicit per-row -1 or +1"}
        dependencies = {}
    else:
        if edges is None or nodes is None or field not in ("somaSide", "superclass"):
            raise ValueError("complete carrier paths and a supported sector field are required")
        edges, nodes = edges.resolve(strict=True), nodes.resolve(strict=True)
        # The immutable source identities determine which metadata may be read.
        for role, path in (("edges", edges), ("nodes", nodes)):
            expected = PUBLISHED_CARRIER[role]
            if path.stat().st_size != expected["size"] or sha256_file(path) != expected["sha256"]:
                raise SourceIdentityError(role)
        import pyarrow.parquet as parquet
        values = parquet.read_table(nodes, columns=[field]).column(field).to_pylist()
        labels = []
        for value in values:
            text = "" if value is None else str(value).strip()
            labels.append(text if text and text.lower() != "nan" else "<missing>")
        sources = [
            {"role": role, "name": path.name, **PUBLISHED_CARRIER[kind]}
            for kind, role, path in (("edges", "CARRIER_EDGES", edges), ("nodes", "CARRIER_NODES", nodes))
        ]
        header = {"schema": SCHEMA, "source_field": field, "source_identity": "paper16-carrier-index.v1",
                  "sign_semantics": "paper16-presynaptic-consensus-transmitter-proxy.v1",
                  "sector_labels": sorted(set(labels)),
                  "record_count": PUBLISHED_CARRIER["eligible_source_count"], "source_artifacts": sources}
        source_paths = {"CARRIER_EDGES": str(edges), "CARRIER_NODES": str(nodes)}
        edge_count = PUBLISHED_CARRIER["known_edge_count"]
        command = ["-B", "-m", "applications.malecns_profile_census.prepare_input",
                   "--edges-npz", "{source:CARRIER_EDGES}", "--nodes-parquet", "{source:CARRIER_NODES}",
                   "--field", field, "--output", "{output}"]
        sign_mapping = dict(PROXY_SIGN)
        dependencies = {name: importlib.metadata.version(name) for name in ("numpy", "pandas", "scipy", "pyarrow")}
    closure = ["applications/malecns_profile_census/prepare_input.py",
               "applications/malecns_profile_census/protocol.py",
               "applications/malecns_profile_census/prepared_cache.py"]
    identity = {
        "schema": "sof-runtime.prepared-input-identity.v1", "sources": header["source_artifacts"],
        "sector_policy": {"id": "malecns-profile-sector-policy", "version": "1",
                          "field": header["source_field"], "missing": "none/empty/casefold-nan to <missing>",
                          "label_order": "sorted Unicode strings"},
        "sign_policy": {"id": header["sign_semantics"], "version": "1", "mapping": sign_mapping},
        "packet_format": {"schema": SCHEMA, "magic": "RIMEPC01", "byte_order": "little", "version": 1},
        "expected_header": header, "expected_edge_count": edge_count,
        "preparer": {"id": "malecns-profile-preparer", "version": "1",
                     "sources_sha256": {name: sha256_file(ROOT / name) for name in closure},
                     "executable_sha256": sha256_file(sys.executable), "command": command,
                     "runtime": {"python": platform.python_version(), "dependencies": dependencies}},
    }
    return {
        "schema": "sof-runtime.prepared-input-cache-request.v1",
        "cache_root": str(cache_root.resolve()), "identity": identity,
        "source_paths": source_paths, "preparer_paths": {name: str(ROOT / name) for name in closure},
        "builder_program": sys.executable, "working_directory": str(ROOT),
        "invalid_policy": invalid_policy, "lock_timeout_seconds": 300, "build_timeout_seconds": 600,
        "consumer": {"program": str(rust_binary()), "sha256": sha256_file(rust_binary()),
                     "args": ["{packet}", "--metrics"], "timeout_seconds": 300} if execute else None,
    }


def call_cache(request: dict) -> tuple[dict, float, int]:
    with tempfile.TemporaryDirectory(prefix="prepared-cache-request-") as directory:
        path = Path(directory) / "request.json"
        path.write_bytes(canonical_bytes(request))
        started = perf_counter()
        completed = subprocess.run([str(cache_binary()), str(path)], cwd=ROOT, capture_output=True, timeout=1000)
        elapsed = perf_counter() - started
    if completed.stderr:
        raise RuntimeError(completed.stderr.decode("utf-8", errors="replace"))
    result = json.loads(completed.stdout)
    if completed.returncode == 0:
        if result.get("key") != cache_key(request["identity"]):
            raise ValueError("Python/Rust cache identity disagreement")
        if result.get("status") not in ("CACHE_HIT_VALIDATED", "CACHE_MISS_PREPARED", "CACHE_INVALID_REBUILT"):
            raise ValueError("unexpected successful cache status")
    return result, elapsed, completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-root", type=Path, required=True)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--edges-npz", type=Path)
    parser.add_argument("--nodes-parquet", type=Path)
    parser.add_argument("--field", default="somaSide", choices=("somaSide", "superclass"))
    parser.add_argument("--invalid-policy", default="reject", choices=("reject", "rebuild"))
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        if not cache_binary().is_file():
            raise ValueError("build the prepared-input-cache crate before use")
        started = perf_counter()
        request = make_request(args.cache_root, fixture=args.fixture, edges=args.edges_npz, nodes=args.nodes_parquet,
                               field=args.field, invalid_policy=args.invalid_policy, execute=args.execute)
        identity_seconds = perf_counter() - started
        result, process_seconds, code = call_cache(request)
        print(json.dumps({"result": result, "identity_construction_seconds": identity_seconds,
                          "cache_process_wall_seconds": process_seconds,
                          "workflow_wall_seconds": perf_counter() - started}, sort_keys=True))
        return code
    except SourceIdentityError as error:
        print(json.dumps({"status": "SOURCE_IDENTITY_REJECTED", "detail": str(error)}))
        return 2
    except Exception as error:
        print(json.dumps({"status": "REQUEST_FAILED", "detail": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
