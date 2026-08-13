#!/usr/bin/env python3
"""Check the source-addressed service implementation closure used by MCP evals."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sof_runtime import __version__
from sof_runtime.artifacts import canonical_json_bytes, sha256_bytes, sha256_file
from sof_runtime.contracts import load_json
from sof_runtime.paths import PROJECT_ROOT


def _implementation_paths() -> list[Path]:
    paths = [
        PROJECT_ROOT / "pyproject.toml",
        PROJECT_ROOT / "contracts" / "upstream.lock.json",
    ]
    paths.extend(
        sorted((PROJECT_ROOT / "contracts" / "service" / "v1.0").glob("*.json"))
    )
    paths.extend(
        sorted((PROJECT_ROOT / "contracts" / "runtime" / "v1.0").glob("*.json"))
    )
    paths.extend(sorted((PROJECT_ROOT / "src" / "sof_runtime").rglob("*.py")))
    return paths


def _write_closure(path: Path) -> None:
    files = [
        {
            "path": item.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": sha256_file(item),
        }
        for item in _implementation_paths()
    ]
    basis = {"runtime_version": __version__, "files": files}
    closure = {
        "contract_id": "sof-runtime.service-implementation-closure.v1",
        **basis,
        "closure_sha256": sha256_bytes(canonical_json_bytes(basis)),
    }
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(closure, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("closure", type=Path)
    parser.add_argument(
        "--write",
        action="store_true",
        help="refresh the closure from the complete Python runtime and service contracts",
    )
    args = parser.parse_args()
    if args.write:
        _write_closure(args.closure)
    closure = load_json(args.closure)
    errors: list[str] = []
    basis = {
        "runtime_version": closure["runtime_version"],
        "files": closure["files"],
    }
    for item in closure["files"]:
        path = (PROJECT_ROOT / item["path"]).resolve()
        try:
            path.relative_to(PROJECT_ROOT)
        except ValueError:
            errors.append(f"closure path escapes repository: {item['path']}")
            continue
        if not path.is_file():
            errors.append(f"closure path is missing: {item['path']}")
        elif sha256_file(path) != item["sha256"]:
            errors.append(f"closure digest mismatch: {item['path']}")
    actual = sha256_bytes(canonical_json_bytes(basis))
    if actual != closure["closure_sha256"]:
        errors.append(
            f"implementation closure digest is {actual}, expected {closure['closure_sha256']}"
        )
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print(f"PASS: service implementation closure {actual}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
