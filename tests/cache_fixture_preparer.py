"""Fault-controlled preparer used only by cache lifecycle tests."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time

from applications.malecns_profile_census.prepare_input import fixture_data
from applications.malecns_profile_census.protocol import write_packet


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", default="normal", choices=("normal", "fail", "pause-once", "source-drift"))
    parser.add_argument("--marker", type=Path)
    parser.add_argument("--delay", type=float, default=0)
    args = parser.parse_args()
    first_pause = args.mode == "pause-once" and not args.marker.exists()
    if args.mode == "fail" or first_pause:
        args.output.write_bytes(b"incomplete packet")
    if args.marker and (first_pause or args.mode != "pause-once"):
        args.marker.write_text(json.dumps({"pid": os.getpid()}))
    if args.mode == "fail":
        return 7
    if first_pause:
        time.sleep(60)
        return 8
    time.sleep(args.delay)
    header, records = fixture_data(args.fixture)
    write_packet(args.output, header, records)
    if args.mode == "source-drift":
        args.fixture.write_bytes(args.fixture.read_bytes() + b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
