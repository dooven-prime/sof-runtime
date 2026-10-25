"""Pinned full-carrier preparation, separate from old profile-census sources."""
from __future__ import annotations

import argparse
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd
from scipy import sparse

from ..malecns_profile_census.prepare_input import PROXY_SIGN, PUBLISHED_CARRIER
from .protocol import arrays_from_source, canonical, file_sha, write_packet


def pinned_sources(edges, nodes):
    records = []
    for role, path in (("edges",Path(edges)),("nodes",Path(nodes))):
        expected = PUBLISHED_CARRIER[role]
        if path.stat().st_size != expected["size"] or file_sha(path) != expected["sha256"]:
            raise ValueError(f"{role} differs from published carrier bytes")
        records.append({"role":role,"name":path.name,**expected})
    return records


def load_source(edges, nodes):
    started = perf_counter(); provenance = pinned_sources(edges,nodes)
    verified = perf_counter()
    table = pd.read_parquet(nodes, columns=["consensus_nt"])
    if len(table) != PUBLISHED_CARRIER["node_count"]:
        raise ValueError("node basis size mismatch")
    signs = np.fromiter((PROXY_SIGN.get(str(x).strip().lower(),0) for x in table.consensus_nt),dtype=np.int8)
    with np.load(edges,allow_pickle=False) as archive:
        row, col, weight = (archive[key].astype(np.int64) for key in ("row","col","weight"))
    if len(row) != len(col) or len(row) != len(weight) or np.any(weight <= 0) or np.any(weight > 2**32-1):
        raise ValueError("raw edge values")
    if np.any(row < 0) or np.any(col < 0) or np.any(row >= len(signs)) or np.any(col >= len(signs)):
        raise ValueError("raw endpoints")
    loaded = perf_counter(); known = signs[row] != 0
    matrix = sparse.csr_matrix((weight[known],(row[known],col[known])),shape=(len(signs),len(signs)),dtype=np.int64)
    matrix.sum_duplicates(); matrix.sort_indices()
    if matrix.nnz != PUBLISHED_CARRIER["known_edge_count"] or matrix.nnz != np.count_nonzero(known):
        raise ValueError("known-sign support/duplicate mismatch")
    built = perf_counter()
    if pinned_sources(edges,nodes) != provenance:
        raise ValueError("source changed during preparation")
    return matrix,signs,provenance,{"initial_source_hash_seconds":verified-started,
                                  "decode_seconds":loaded-verified,"source_csr_seconds":built-loaded,
                                  "post_source_hash_seconds":perf_counter()-built}


def prepare(edges,nodes,output):
    started = perf_counter(); matrix,signs,provenance,timing = load_source(edges,nodes)
    _,arrays,conversion = arrays_from_source(matrix,signs)
    before = perf_counter()
    header = write_packet(output,arrays,{"artifacts":provenance,"sign_policy":"paper16-presynaptic-consensus-transmitter-proxy.v1"})
    timing.update(target_transpose_csr_seconds=conversion,validate_serialize_seconds=perf_counter()-before,
                  whole_prepare_seconds=perf_counter()-started)
    return {"status":"PREPARED_LOCAL","packet_sha256":file_sha(output),"header":header,"timings":timing}


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edges",required=True,type=Path); parser.add_argument("--nodes",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    print(canonical(prepare(args.edges,args.nodes,args.output)).decode())
