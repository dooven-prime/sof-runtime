"""Recheck saved local file closure and full output comparisons; no reexecution."""
import argparse
import json
from pathlib import Path

from .protocol import file_sha
from .reference import compare
from .runner import bindings


def verify(directory):
    root=Path(directory).resolve(strict=True)
    record=json.loads((root/"benchmark.v0.json").read_bytes())
    if record["status"]!="PASS_LOCAL_BOUNDED_CONTROLS" or record["implementation_sha256"]!=bindings():
        raise ValueError("status/implementation binding changed")
    if {p.name for p in root.iterdir()}!=set(record["files"])|{"benchmark.v0.json"}:
        raise ValueError("file inventory mismatch")
    for name,expected in record["files"].items():
        path=root/name
        if path.is_symlink() or not path.is_file() or path.resolve().parent!=root or file_sha(path)!=expected:
            raise ValueError("file hash/confinement mismatch")
    for item in record["observations"]:
        if item["mode"]=="exact":
            stem=f"exact-{item['operation']}-{item['threads']}"; reference=f"exact-{item['operation']}.reference.json"
        else:
            stem=f"{item['vector']}-{item['operation']}-rust-{item['threads']}"; reference=f"{item['vector']}-{item['operation']}.reference.json"
        actual=json.loads((root/f"{stem}.result.json").read_bytes())["output"]
        expected=json.loads((root/reference).read_bytes())
        if item["mode"]=="exact":
            if actual!=expected: raise ValueError("rational output mismatch")
        elif not compare(expected,actual)["accepted"]:
            raise ValueError("numerical output mismatch")
    return {"status":"VERIFIED_LOCAL_SAVED_COMPARISONS","outputs":len(record["observations"]),
            "worker_reexecuted":False,"independent_validation":False,"public_release_claimed":False}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("directory",type=Path)
    print(json.dumps(verify(parser.parse_args().directory),indent=2))
