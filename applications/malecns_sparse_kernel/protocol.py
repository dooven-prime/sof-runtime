"""New target-row packet and independently readable reference arrays."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
from time import perf_counter

import numpy as np
from scipy import sparse

MAGIC = b"MSPMV001"
SCHEMA = "sof-runtime.malecns-spmv.packet.v0"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def file_sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def validate(header, ptr, sources, weights, signs, masses):
    n, m = header["n"], header["nnz"]
    if any(array.dtype != np.dtype(dtype) for array,dtype in zip((ptr,sources,weights,signs,masses),("<u8","<u4","<u4","i1","<u8"))):
        raise ValueError("packet array dtype/byte order")
    if header["schema"] != SCHEMA or type(n) is not int or not 1 <= n <= 1_000_000 or type(m) is not int or not 0 <= m <= 100_000_000:
        raise ValueError("packet schema/dimension limit")
    if (len(ptr), len(sources), len(weights), len(signs), len(masses)) != (n+1, m, m, n, n):
        raise ValueError("array lengths")
    if ptr[0] != 0 or ptr[-1] != m or np.any(ptr[1:] < ptr[:-1]) or np.any(sources >= n):
        raise ValueError("pointer/index range")
    if np.any(weights == 0) or np.any(~np.isin(signs, [-1, 0, 1])):
        raise ValueError("weight/sign range")
    # A boundary resets the ascending-source requirement, including empty rows.
    if m > 1:
        bad = sources[1:] <= sources[:-1]
        starts = ptr[1:-1]; starts = starts[(starts > 0) & (starts < m)]
        bad[starts.astype(np.int64)-1] = False
        if np.any(bad):
            raise ValueError("unsorted or duplicate source in a target row")
    if m:
        if np.any(signs[sources] == 0):
            raise ValueError("unknown-sign edge")
        # n,m and u32 weights imply total <= 2**59; no u64 overflow here.
        sums = np.zeros(n, dtype=np.uint64)
        np.add.at(sums, sources, weights)
    else:
        sums = np.zeros(n, dtype=np.uint64)
    if not np.array_equal(sums, masses):
        raise ValueError("outgoing mass mismatch")


def arrays_from_source(matrix, signs):
    matrix = sparse.csr_matrix(matrix, dtype=np.int64)
    matrix.sum_duplicates(); matrix.sort_indices()
    if matrix.shape[0] != matrix.shape[1] or matrix.shape[0] != len(signs):
        raise ValueError("square source carrier required")
    if np.any(matrix.data <= 0) or np.any(matrix.data > 2**32-1):
        raise ValueError("positive u32 weights required")
    if np.any(~np.isin(signs, [-1, 0, 1])):
        raise ValueError("invalid signs")
    if np.any((np.diff(matrix.indptr) > 0) & (np.asarray(signs) == 0)):
        raise ValueError("unknown-sign rows must already be removed")
    started = perf_counter()
    target = matrix.transpose(copy=False).tocsr(copy=True)
    conversion = perf_counter()-started
    masses = np.asarray(matrix.sum(axis=1)).ravel().astype("<u8")
    arrays = (target.indptr.astype("<u8"), target.indices.astype("<u4"),
              target.data.astype("<u4"), np.asarray(signs, dtype="i1"), masses)
    return target, arrays, conversion


def write_packet(path, arrays, provenance):
    ptr, sources, weights, signs, masses = arrays
    header = {"schema": SCHEMA, "n": len(signs), "nnz": len(sources), "provenance": provenance}
    validate(header, *arrays)
    encoded = canonical(header)
    with Path(path).open("xb") as stream:
        stream.write(MAGIC); stream.write(struct.pack("<I", len(encoded))); stream.write(encoded)
        for array in arrays:
            stream.write(array.tobytes(order="C"))
    return header


def read_packet(path, expected):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("packet SHA-256 mismatch")
    if len(raw) < 12 or raw[:8] != MAGIC:
        raise ValueError("packet magic/truncation")
    length, = struct.unpack_from("<I", raw, 8)
    if not 0 < length <= 65536 or len(raw) < 12+length:
        raise ValueError("header size")
    header = json.loads(raw[12:12+length])
    n, m = header["n"], header["nnz"]
    if type(n) is not int or type(m) is not int or not 1 <= n <= 1_000_000 or not 0 <= m <= 100_000_000:
        raise ValueError("dimension limit")
    offset = 12+length; arrays = []
    for dtype, count in (("<u8",n+1),("<u4",m),("<u4",m),("i1",n),("<u8",n)):
        size = np.dtype(dtype).itemsize*count
        if offset+size > len(raw):
            raise ValueError("truncated array")
        arrays.append(np.frombuffer(raw, dtype=dtype, count=count, offset=offset))
        offset += size
    if offset != len(raw):
        raise ValueError("trailing packet data")
    validate(header, *arrays)
    return header, tuple(arrays)


def numerical_matrix(arrays):
    ptr, sources, weights, signs, masses = arrays
    coefficients = signs[sources].astype(np.float64)*weights.astype(np.float64)/masses[sources]
    return sparse.csr_matrix((coefficients, sources.astype(np.int32), ptr.astype(np.int32)), shape=(len(signs),len(signs)))
