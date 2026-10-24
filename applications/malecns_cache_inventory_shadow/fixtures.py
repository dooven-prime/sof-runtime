"""Application-owned declarations; old cache bytes are opaque to A0."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import struct

from applications.malecns_profile_census.protocol import canonical_bytes, sha256_file
from .reference import CODEC, SCHEMA, encode, Handle


def digest(value):
    import hashlib
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def declarations(request, producer_sha):
    identity = request["identity"]
    # ExecutionIdentity is a declared invocation-input identity, not an
    # attestation that A0 or the cache producer executed this invocation.
    execution = {"schema": "sof-runtime.cache-shadow-declared-execution.v0",
                 "producer_sha256": producer_sha, "cache_key": digest(identity),
                 "consumer": request["consumer"], "invalid_policy": request["invalid_policy"]}
    return {"producer": {"id": "prepared-input-cache", "version": "0.1.0",
                         "executable_sha256": producer_sha},
            "identities": {"source": {"role": "SourceIdentity", "sha256": digest(identity["sources"])},
                           "execution": {"role": "ExecutionIdentity", "sha256": digest(execution)},
                           "cache": {"role": "CacheIdentity", "sha256": digest(identity)}},
            "schemas": [{"role": r, "id": i, "version": v} for r, i, v in (
                ("cache", "sof-runtime.prepared-input-identity.v1", "1"),
                ("execution", execution["schema"], "0"),
                ("packet", "rime.malecns.profile-census-input.v1", "1"),
                ("source", "sof-runtime.cache-shadow-source-list.v0", "0"))]}


def fixture_declarations():
    return {"producer": {"id": "mechanical-fixture-not-provenance", "version": "0", "executable_sha256": "0"*64},
            "identities": {n: {"role": r, "sha256": "0"*64} for n, r in (
                ("source", "SourceIdentity"), ("execution", "ExecutionIdentity"), ("cache", "CacheIdentity"))},
            "schemas": [{"role": "fixture", "id": "opaque-bytes", "version": "0"}]}


def controls(data, directory, declared):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=False)
    entries = []
    for p in sorted(Path(data).iterdir()):
        h = Handle(p)
        try: h.ntfs(); h.stamp()
        finally: h.close()
        entries.append({"name": p.name, "kind": "RegularFile", "byte_length": p.stat().st_size,
                        "sha256": sha256_file(p)})
    m = {"schema": SCHEMA, "codec": CODEC, "declarations": deepcopy(declared), "entries": entries}
    b = {"schema": "sof-runtime.a0-cache-inspection-bindings.v0", "manifest_schema": SCHEMA,
         "codec": CODEC, "declarations": deepcopy(declared)}
    manifest, bindings = directory/"inventory.json", directory/"bindings.json"
    manifest.write_bytes(encode(m)); bindings.write_bytes(encode(b))
    return manifest, bindings


def copy_flat(source, destination):
    source, destination = Path(source), Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    for p in source.iterdir():
        h = Handle(p)
        try: h.ntfs(); h.stamp()
        finally: h.close()
        shutil.copyfile(p, destination/p.name)
    return destination


def tiny(root):
    data = Path(root)/"data"; data.mkdir(parents=True)
    (data/"packet.bin").write_bytes(b"opaque-fixture-not-a-valid-packet\0\xff"*100)
    (data/"manifest.json").write_bytes(b'{"opaque":true}')
    m, b = controls(data, Path(root)/"controls", fixture_declarations())
    return data, m, b


def invalidate_record(packet):
    """Keep preamble/header and byte length; invalidate the first row's sign."""
    with Path(packet).open("r+b") as stream:
        prefix = stream.read(12)
        magic, length = struct.unpack("<8sI", prefix)
        if magic != b"RIMEPC01": raise ValueError("expected original packet")
        stream.seek(12+length+8+2); previous = stream.read(1)
        if previous not in (b"\x01", b"\xff"): raise ValueError("original row not valid")
        stream.seek(-1, 1); stream.write(b"\0")


def rebind_packet_digest(entry):
    """Negative fixture only: make the old manifest's byte claim truthful."""
    p = Path(entry)/"packet.bin"; m = Path(entry)/"manifest.json"
    value = json.loads(m.read_bytes()); value["packet"]["size"] = p.stat().st_size
    value["packet"]["sha256"] = sha256_file(p); m.write_bytes(canonical_bytes(value))
