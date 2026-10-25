"""Bounded parity controls for the new parallel protocol, not Paper XL evidence."""
from __future__ import annotations

import argparse
from pathlib import Path

from ..q2.engine import check
from ..q2_examples import controls
from .coordinator import build_worker, canonical, execute, file_sha, source_closure, load_json, verify_run


def run(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    build_worker()
    closure = source_closure()
    observations = []
    for name, raw in controls().items():
        serial = check(raw)
        for shards in (2, 3, 4):
            result = execute(raw, shards, output / f"{name}-{shards}")
            if result.get("q2_status") != serial["status"]:
                raise ValueError(f"{name}/{shards}: serial/parallel mismatch: {result}")
            if "witness" in serial and result["rejection"]["witness"]["clause"] != serial["witness"]["clause"]:
                raise ValueError("clause mismatch")
            directory = output / f"{name}-{shards}"
            checked = verify_run(directory)
            if checked["status"] != "VERIFIED_LOCAL_CLOSURE" or checked["decision"] != result["status"]:
                raise ValueError("saved closure verification failed")
            local_conflicts = sum(len(load_json(path.read_bytes())["local_conflicts"])
                                  for path in directory.glob("shard-*.output.json"))
            observations.append({"name": name, "shards": shards, "status": result["status"],
                                 "q2_status": result["q2_status"], "domain": result["domain"],
                                 "coverage_complete": result["coverage_complete"],
                                 "reference_check": result["reference_check"],
                                 "replay": result.get("replay", {}).get("status"),
                                 "local_conflicts": local_conflicts, "saved_closure_verified": True,
                                 "clause": result.get("rejection", {}).get("witness", {}).get("clause"),
                                 "witness_words": [result["rejection"]["witness"][side]["word"]
                                                   for side in ("left", "right")] if result["status"] == "FAIL" else None,
                                 "receipt_sha256": file_sha(output / f"{name}-{shards}/receipt.json")})
            print(f"{name}/{shards}: {result['q2_status']}", flush=True)
    if source_closure() != closure:
        raise ValueError("implementation changed during controls")
    record = {"schema": "sof-runtime.q2-parallel.v0.controls", "status": "PASS_LOCAL_CONTROLS",
              "observations": observations, "source_closure": closure, "performance_claim": False,
              "paper_evidence_promotion": False, "public_release_claimed": False}
    (output / "controls.json").write_bytes(canonical(record))
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    run(parser.parse_args().output_dir)
