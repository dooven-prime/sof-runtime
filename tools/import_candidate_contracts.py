"""Verify or refresh explicitly non-canonical downstream contract snapshots."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "contracts" / "upstream-candidate.lock.json"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Verify or copy candidate Paper XII--XIV contracts from a rime-lite "
            "working tree without promoting them into the immutable upstream lock."
        )
    )
    parser.add_argument(
        "--upstream-root",
        type=Path,
        default=ROOT.parent / "rime-lite",
    )
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    if lock["status"] != "candidate_not_canonical":
        raise SystemExit("candidate lock status is not explicit")

    upstream = args.upstream_root.resolve()
    for entry in lock["entries"]:
        source = upstream / entry["upstream_path"]
        data = source.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != entry["sha256"]:
            raise SystemExit(
                f"candidate source digest mismatch for {entry['upstream_path']}: "
                f"expected {entry['sha256']}, got {digest}"
            )
        target = ROOT / entry["local_path"]
        if args.write:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        elif not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise SystemExit(f"local candidate differs: {entry['local_path']}")

    action = "refreshed" if args.write else "verified"
    print(
        f"PASS: {action} {len(lock['entries'])} candidate contracts; "
        "no canonical promotion asserted"
    )


if __name__ == "__main__":
    main()
