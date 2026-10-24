from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .protocol import SCHEMA, sha256_file, write_packet


PROXY_SIGN = {
    "acetylcholine": 1,
    "dopamine": 1,
    "gaba": -1,
    "glutamate": 1,
    "histamine": 1,
    "octopamine": 1,
    "serotonin": 1,
}
PUBLISHED_CARRIER = {
    "node_count": 211577,
    "known_edge_count": 25214058,
    "eligible_source_count": 163439,
    "edges": {
        "size": 312341374,
        "sha256": "c94e885cc2e8cde78012ed0a68a4beb42eccfe1b64607bdc90ac46e675d6966d",
    },
    "nodes": {
        "size": 3008738,
        "sha256": "87aa46280d68a210f6c8ef4a044282fbbb62342bbeeaab8393b0fd7fa770515e",
    },
}


def _source_ref(role: str, path: Path) -> dict:
    return {
        "role": role,
        "name": path.name,
        "size": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def fixture_data(path: Path) -> tuple[dict, list[dict]]:
    fixture = json.loads(path.read_text(encoding="utf-8"))
    if fixture.get("schema") != "rime.malecns.profile-census-fixture.v1":
        raise ValueError("unsupported profile-census fixture schema")
    records = fixture.get("records")
    if not isinstance(records, list):
        raise ValueError("fixture records must be a list")
    header = {
        "schema": SCHEMA,
        "source_field": fixture["source_field"],
        "source_identity": "fixture_id",
        "sign_semantics": "fixture-explicit-source-sign.v1",
        "sector_labels": fixture["sector_labels"],
        "record_count": len(records),
        "source_artifacts": [_source_ref("CASE_FIXTURE", path)],
    }
    normalized = []
    for record in records:
        normalized.append({
            "source_id": record["source_id"],
            "source_sector": record["source_sector"],
            "sign": record["sign"],
            "edges": [
                (edge["target_sector"], edge["weight"])
                for edge in record["edges"]
            ],
        })
    return header, normalized


def carrier_data(edges_path: Path, nodes_path: Path, field: str) -> tuple[dict, object]:
    for role, path in (("edges", edges_path), ("nodes", nodes_path)):
        expected = PUBLISHED_CARRIER[role]
        if path.stat().st_size != expected["size"] or sha256_file(path) != expected["sha256"]:
            raise ValueError(f"{role} carrier bytes do not match the Paper XVI release anchor")
    try:
        import numpy as np
        import pandas as pd
        from scipy import sparse
    except ImportError as error:
        raise RuntimeError("NumPy, SciPy, pandas, and PyArrow are required for carrier preparation") from error

    node_table = pd.read_parquet(nodes_path)
    if len(node_table) != PUBLISHED_CARRIER["node_count"]:
        raise ValueError("node count does not match the Paper XVI carrier domain")
    required = {"consensus_nt", field}
    missing = required - set(node_table.columns)
    if missing:
        raise ValueError(f"carrier node table is missing columns: {sorted(missing)}")
    labels = []
    for value in node_table[field]:
        if value is None or pd.isna(value):
            labels.append("<missing>")
        else:
            text = str(value).strip()
            labels.append(text if text and text.lower() != "nan" else "<missing>")
    sector_labels = sorted(set(labels))
    sector_code = {label: index for index, label in enumerate(sector_labels)}
    sector_codes = np.fromiter((sector_code[label] for label in labels), dtype=np.uint16)
    signs = np.fromiter(
        (PROXY_SIGN.get(str(value).strip().lower(), 0) for value in node_table["consensus_nt"]),
        dtype=np.int8,
        count=len(node_table),
    )

    with np.load(edges_path, allow_pickle=False) as archive:
        rows = archive["row"].astype(np.int64, copy=False)
        cols = archive["col"].astype(np.int64, copy=False)
        weights = archive["weight"].astype(np.int64, copy=False)
    if not (len(rows) == len(cols) == len(weights)):
        raise ValueError("carrier edge arrays have inconsistent lengths")
    if np.any(rows < 0) or np.any(rows >= len(node_table)) or np.any(cols < 0) or np.any(cols >= len(node_table)):
        raise ValueError("carrier edge endpoint is outside the node basis")
    if np.any(weights <= 0):
        raise ValueError("carrier weights must be positive integers")

    known = signs[rows] != 0
    matrix = sparse.csr_matrix(
        (weights[known], (rows[known], cols[known])),
        shape=(len(node_table), len(node_table)),
        dtype=np.int64,
    )
    matrix.sum_duplicates()
    if matrix.nnz != PUBLISHED_CARRIER["known_edge_count"]:
        raise ValueError("known-sign edge count does not match the Paper XVI carrier domain")
    if matrix.nnz != int(np.count_nonzero(known)):
        raise ValueError("duplicate source-target pairs are not admitted by the carrier packet builder")
    if np.any(matrix.data <= 0):
        raise OverflowError("CSR edge aggregation overflowed the positive signed 64-bit range")
    matrix.sort_indices()
    indptr = matrix.indptr.astype(np.int64, copy=False)
    indices = matrix.indices.astype(np.int64, copy=False)
    data = matrix.data.astype(np.int64, copy=False)
    source_indices = [
        int(index)
        for index in range(len(node_table))
        if signs[index] != 0 and indptr[index] < indptr[index + 1]
    ]
    if len(source_indices) != PUBLISHED_CARRIER["eligible_source_count"]:
        raise ValueError("eligible-source count does not match the Paper XVI carrier domain")
    header = {
        "schema": SCHEMA,
        "source_field": field,
        "source_identity": "paper16-carrier-index.v1",
        "sign_semantics": "paper16-presynaptic-consensus-transmitter-proxy.v1",
        "sector_labels": sector_labels,
        "record_count": len(source_indices),
        "source_artifacts": [
            _source_ref("CARRIER_EDGES", edges_path),
            _source_ref("CARRIER_NODES", nodes_path),
        ],
    }

    def records():
        for source in source_indices:
            start, stop = int(indptr[source]), int(indptr[source + 1])
            edge_records = [
                (int(sector_codes[int(target)]), int(weight))
                for target, weight in zip(indices[start:stop], data[start:stop])
            ]
            mass = sum(weight for _, weight in edge_records)
            if mass > (1 << 63) - 1:
                raise OverflowError(f"source row {source} exceeds the signed 64-bit bound")
            yield {
                "source_id": source,
                "source_sector": int(sector_codes[source]),
                "sign": int(signs[source]),
                "edges": edge_records,
            }

    return header, records()


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a source-addressed profile-census packet")
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--edges-npz", type=Path)
    parser.add_argument("--nodes-parquet", type=Path)
    parser.add_argument("--field", default="somaSide", choices=("somaSide", "superclass"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.fixture:
            if args.edges_npz or args.nodes_parquet:
                raise ValueError("choose either --fixture or carrier inputs")
            header, records = fixture_data(args.fixture)
        else:
            if not args.edges_npz or not args.nodes_parquet:
                raise ValueError("carrier mode requires --edges-npz and --nodes-parquet")
            header, records = carrier_data(args.edges_npz, args.nodes_parquet, args.field)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        write_packet(args.output, header, records)
        print(json.dumps({
            "status": "INPUT_PREPARED",
            "path": str(args.output.resolve()),
            "size": args.output.stat().st_size,
            "sha256": sha256_file(args.output),
            "records": header["record_count"],
            "source_field": header["source_field"],
        }, sort_keys=True))
    except Exception as error:
        print(f"profile-census-prepare: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
