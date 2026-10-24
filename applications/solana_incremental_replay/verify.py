"""Recheck selected local files and full reference, without claiming attestation."""
import argparse
from pathlib import Path

from applications.solana_offchain_slice.common import canonical
from .validation import verify


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    print(canonical(verify(args.manifest, args.directory)).decode())
