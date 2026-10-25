from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = PROJECT_ROOT / "plugins" / "rust" / "positive-word-support" / "Cargo.toml"
Q2_MANIFEST = (
    PROJECT_ROOT
    / "plugins"
    / "rust"
    / "event-causal-q2-enumerator"
    / "Cargo.toml"
)
CENSUS_MANIFEST = (
    PROJECT_ROOT
    / "plugins"
    / "rust"
    / "malecns-profile-census"
    / "Cargo.toml"
)


def find_cargo() -> Path:
    configured = os.environ.get("CARGO")
    candidates = [
        Path(configured).expanduser() if configured else None,
        Path(shutil.which("cargo")) if shutil.which("cargo") else None,
        Path.home()
        / ".cargo"
        / "bin"
        / ("cargo.exe" if os.name == "nt" else "cargo"),
    ]
    cargo = next((path for path in candidates if path and path.is_file()), None)
    if cargo is None:
        raise SystemExit("Cargo was not found; set CARGO to the cargo executable")
    return cargo


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the stable SOF Rust plugin; prototypes are opt-in.")
    parser.add_argument("--engineering", action="store_true", help="also build the Q2 enumerator and MaleCNS census prototypes")
    args = parser.parse_args()
    cargo = str(find_cargo())
    manifests = (MANIFEST, Q2_MANIFEST, CENSUS_MANIFEST) if args.engineering else (MANIFEST,)
    for manifest in manifests:
        subprocess.run(
            [cargo, "build", "--release", "--locked", "--manifest-path", str(manifest)],
            cwd=PROJECT_ROOT,
            check=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
