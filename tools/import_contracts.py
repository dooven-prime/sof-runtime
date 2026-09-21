from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "contracts" / "upstream.lock.json"


def git_blob(repository: Path, revision: str, path: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repository), "show", f"{revision}:{path}"],
        capture_output=True,
    )
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise SystemExit(f"cannot read {revision}:{path}: {message}")
    return result.stdout


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify or restore digest-locked contracts from a frozen rime-lite commit."
    )
    parser.add_argument(
        "--upstream-root",
        type=Path,
        default=ROOT.parent / "rime-lite",
        help="local Git clone containing the locked upstream commit",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="restore local vendored files from the locked Git blobs",
    )
    args = parser.parse_args()

    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    repository = args.upstream_root.resolve()
    verified = 0
    for import_group in lock["imports"]:
        snapshot_id = import_group["snapshot"]
        try:
            revision = lock["snapshots"][snapshot_id]["release_content_commit"]
        except KeyError as error:
            raise SystemExit(f"unknown or incomplete upstream snapshot: {snapshot_id}") from error
        for entry in import_group["entries"]:
            data = git_blob(repository, revision, entry["upstream_path"])
            digest = hashlib.sha256(data).hexdigest()
            if digest != entry["sha256"]:
                raise SystemExit(
                    "locked upstream digest mismatch for "
                    f"{snapshot_id}:{entry['upstream_path']}: {digest}"
                )
            target = ROOT / entry["local_path"]
            if args.write:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            elif not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                raise SystemExit(f"local vendored file differs: {entry['local_path']}")
            verified += 1

    action = "restored" if args.write else "verified"
    print(
        f"PASS: {action} {verified} files from "
        f"{len(lock['imports'])} immutable snapshots"
    )


if __name__ == "__main__":
    main()
