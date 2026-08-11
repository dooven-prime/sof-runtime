from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCKS = (ROOT / "contracts" / "upstream.lock.json",)


def main() -> None:
    failures: list[str] = []
    verified: list[str] = []
    for lock_path in LOCKS:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        for entry in lock["entries"]:
            path = ROOT / entry["local_path"]
            if not path.is_file():
                failures.append(f"missing: {entry['local_path']}")
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != entry["sha256"]:
                failures.append(
                    f"digest mismatch: {entry['local_path']} "
                    f"(expected {entry['sha256']}, got {digest})"
                )
        verified.append(f"{len(lock['entries'])} from {lock_path.name}")
    if failures:
        raise SystemExit("upstream lock verification failed:\n- " + "\n- ".join(failures))
    print(
        "PASS: verified " + ", ".join(verified)
    )


if __name__ == "__main__":
    main()
