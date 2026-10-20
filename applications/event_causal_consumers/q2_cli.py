"""JSON entry point for local Q2 checks and independent rejection replay."""

import argparse
import json
from pathlib import Path
import sys

from q2 import check, verify_rejection
from q2.common import IMPLEMENTATION_STATUS, InputError, ResourceLimit


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError("duplicate JSON key")
        result[key] = value
    return result


def read_json(path, max_bytes):
    if str(path) == "-":
        data = sys.stdin.buffer.read(max_bytes + 1)
    else:
        with Path(path).open("rb") as stream:
            data = stream.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ResourceLimit("JSON input-byte limit")
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=unique_object,
                          parse_constant=lambda x: (_ for _ in ()).throw(InputError("nonfinite JSON number")))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise InputError("invalid UTF-8 JSON") from exc
    except ValueError as exc:
        if "integer string conversion" in str(exc):
            raise ResourceLimit("JSON integer resource limit") from exc
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "verify"))
    parser.add_argument("request", type=Path)
    parser.add_argument("--result", type=Path)
    parser.add_argument("--max-input-bytes", type=int, default=16777216)
    args = parser.parse_args()
    try:
        if args.max_input_bytes <= 0:
            raise InputError("invalid input-byte limit")
        if (args.mode == "verify") != (args.result is not None):
            raise InputError("--result is required only in verify mode")
        if str(args.request) == "-" and args.result is not None and str(args.result) == "-":
            raise InputError("only one JSON document may use stdin")
        request = read_json(args.request, args.max_input_bytes)
        result = check(request) if args.mode == "check" else verify_rejection(
            request, read_json(args.result, args.max_input_bytes))
    except (InputError, OSError) as exc:
        result = {"status": "INVALID_INPUT", "detail": str(exc), "implementation_status": IMPLEMENTATION_STATUS}
    except (ResourceLimit, RecursionError, MemoryError) as exc:
        result = {"status": "UNRESOLVED_LIMIT", "detail": str(exc) or type(exc).__name__,
                  "implementation_status": IMPLEMENTATION_STATUS}
    try:
        serialized = json.dumps(result, ensure_ascii=True, allow_nan=False, indent=2)
    except (ValueError, RecursionError, MemoryError) as exc:
        result = {"status": "UNRESOLVED_LIMIT", "detail": "result serialization: " + type(exc).__name__,
                  "implementation_status": IMPLEMENTATION_STATUS}
        serialized = json.dumps(result)
    print(serialized)
    if result["status"] == "UNRESOLVED_LIMIT":
        return 2
    return 1 if result["status"].startswith("INVALID") else 0


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
