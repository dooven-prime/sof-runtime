"""Consumer fault injection for temporary cache-fusion test inputs only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("source", "packet", "packet-valid"))
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    target = args.source if args.mode == "source" else args.packet
    raw = bytearray(target.read_bytes())
    if args.mode == "packet-valid":
        weight = struct.unpack_from("<Q", raw, len(raw) - 8)[0]
        struct.pack_into("<Q", raw, len(raw) - 8, weight + 1)
    else:
        raw[0] ^= 1
    target.write_bytes(raw)
    print(json.dumps({"fault_injected": args.mode}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
