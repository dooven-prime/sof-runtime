from __future__ import annotations

import argparse
import json

from sof_runtime.workflow import validate_run_response


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify run artifact digests and independently recompute rank-collapse evidence."
    )
    parser.add_argument("run_response")
    args = parser.parse_args()
    certificate = validate_run_response(args.run_response)
    print(json.dumps(certificate, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
