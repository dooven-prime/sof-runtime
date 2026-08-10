from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = PROJECT_ROOT / "plugins" / "rust" / "positive-word-support" / "Cargo.toml"


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
    subprocess.run(
        [
            str(find_cargo()),
            "build",
            "--release",
            "--locked",
            "--manifest-path",
            str(MANIFEST),
        ],
        cwd=PROJECT_ROOT,
        check=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
