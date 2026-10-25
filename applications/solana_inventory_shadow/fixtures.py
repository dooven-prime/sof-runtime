"""Detached declarations, preserving original producer bytes and identity."""
from pathlib import Path
import shutil

from applications.solana_offchain_slice.common import canonical as original_encoding, parse, file_sha, sha
from .reference import SCHEMA, CODEC, encode


def state_declarations(state):
    cp = Path(state)/"checkpoint.json"; body = parse(cp.read_bytes())["body"]
    return {"producer": {"id": "solana-publication-recovery", "version": "0.1.0",
        "executable_sha256": body["execution_identity"]["program_sha256"]},
        "identities": {"source": {"role": "SourceIdentity", "sha256": sha(original_encoding(body["source_identity"]))},
            "execution": {"role": "ExecutionIdentity", "sha256": sha(original_encoding(body["execution_identity"]))},
            "checkpoint": {"role": "CheckpointIdentity", "sha256": file_sha(cp)}},
        "schemas": [{"role": r, "id": i, "version": "v0"} for r, i in (
            ("checkpoint", "sof-runtime.source-checkpoint.v0"), ("execution", "sof-runtime.execution-identity.v0"),
            ("source", "sof-runtime.source-identity.v0"))]}


def declarations_fixture():
    return {"producer": {"id": "mechanical-fixture-not-provenance", "version": "v0", "executable_sha256": "0"*64},
        "identities": {name: {"role": role, "sha256": "0"*64} for name, role in (
            ("source", "SourceIdentity"), ("execution", "ExecutionIdentity"), ("checkpoint", "CheckpointIdentity"))},
        "schemas": [{"role": "fixture", "id": "mechanical-bytes-only", "version": "v0"}]}


def controls(data, directory, declarations):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=False)
    entries = []
    for p in sorted(Path(data).iterdir()):
        if not p.is_file() or p.is_symlink(): raise ValueError("declaration factory requires an ordinary initial fixture")
        entries.append({"name": p.name, "kind": "RegularFile", "byte_length": p.stat().st_size, "sha256": file_sha(p)})
    m = {"schema": SCHEMA, "codec": CODEC, "declarations": declarations, "entries": entries}
    b = {"schema": "sof-runtime.a0-inspection-bindings.v0", "manifest_schema": SCHEMA, "codec": CODEC, "declarations": declarations}
    manifest, binding = directory/"manifest.json", directory/"bindings.json"
    manifest.write_bytes(encode(m)); binding.write_bytes(encode(b))
    return manifest, binding


def copy_flat(source, destination):
    source, destination = Path(source), Path(destination); destination.mkdir(parents=True, exist_ok=False)
    for p in source.iterdir():
        if not p.is_file() or p.is_symlink(): raise ValueError("ordinary source files required")
        shutil.copyfile(p, destination/p.name)
    return destination


def tiny(root):
    data = Path(root)/"data"; data.mkdir()
    (data/"payload.bin").write_bytes(b"opaque bytes\x00\xff\n"*100)
    m, b = controls(data, Path(root)/"controls", declarations_fixture())
    return data, m, b
