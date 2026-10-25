from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import struct
from typing import BinaryIO, Iterable, Iterator


MAGIC = b"RIMEPC01"
SCHEMA = "rime.malecns.profile-census-input.v1"
HEADER_PREFIX = struct.Struct("<8sI")
ROW_PREFIX = struct.Struct("<QHbI")
EDGE = struct.Struct("<HQ")
MAX_I64 = (1 << 63) - 1


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_header(header: dict) -> None:
    if set(header) != {
        "schema", "source_field", "source_identity", "sign_semantics",
        "sector_labels", "record_count", "source_artifacts",
    }:
        raise ValueError("profile-census header has unknown or missing fields")
    if header.get("schema") != SCHEMA:
        raise ValueError("unsupported profile-census input schema")
    if not isinstance(header.get("source_field"), str) or not header["source_field"]:
        raise ValueError("source_field must be a nonempty string")
    for field in ("source_identity", "sign_semantics"):
        if not isinstance(header.get(field), str) or not header[field]:
            raise ValueError(f"{field} must be a nonempty string")
    labels = header.get("sector_labels")
    if (not isinstance(labels, list) or not labels or
            any(not isinstance(label, str) or not label for label in labels) or
            len(set(labels)) != len(labels)):
        raise ValueError("sector_labels must be unique nonempty strings")
    count = header.get("record_count")
    if type(count) is not int or not 0 <= count <= MAX_I64:
        raise ValueError("record_count must be a nonnegative signed 64-bit integer")
    artifacts = header.get("source_artifacts")
    if not isinstance(artifacts, list):
        raise ValueError("source_artifacts must be a list")
    for artifact in artifacts:
        if (not isinstance(artifact, dict) or
                set(artifact) != {"role", "name", "size", "sha256"} or
                not isinstance(artifact.get("role"), str) or
                not isinstance(artifact.get("name"), str) or
                type(artifact.get("size")) is not int or not 0 <= artifact["size"] <= MAX_I64 or
                not isinstance(artifact.get("sha256"), str) or
                len(artifact["sha256"]) != 64 or
                any(char not in "0123456789abcdef" for char in artifact["sha256"])):
            raise ValueError("invalid source artifact reference")


def write_packet(path: str | Path, header: dict, records: Iterable[dict]) -> None:
    """Write the canonical header and checked little-endian source/edge stream."""
    _validate_header(header)
    target = Path(path)
    if target.exists():
        raise FileExistsError(target)
    temporary = target.with_name(target.name + ".tmp")
    try:
        with temporary.open("xb") as stream:
            encoded = canonical_bytes(header)
            stream.write(HEADER_PREFIX.pack(MAGIC, len(encoded)))
            stream.write(encoded)
            previous_source = -1
            count = 0
            sector_count = len(header["sector_labels"])
            for record in records:
                source = record.get("source_id")
                source_sector = record.get("source_sector")
                sign = record.get("sign")
                edges = record.get("edges")
                if type(source) is not int or not 0 <= source <= MAX_I64 or source <= previous_source:
                    raise ValueError("source_id values must be increasing signed 64-bit integers")
                if type(source_sector) is not int or not 0 <= source_sector < sector_count:
                    raise ValueError("source_sector is outside the declared sector basis")
                if type(sign) is not int or sign not in (-1, 1):
                    raise ValueError("only known positive or negative source signs are admitted")
                if not isinstance(edges, list) or not edges:
                    raise ValueError("eligible source rows must contain at least one edge")
                if len(edges) > (1 << 32) - 1:
                    raise ValueError("edge count exceeds the input format")
                stream.write(ROW_PREFIX.pack(source, source_sector, sign, len(edges)))
                mass = 0
                for edge in edges:
                    target_sector, weight = edge
                    if type(target_sector) is not int or not 0 <= target_sector < sector_count:
                        raise ValueError("target sector is outside the declared sector basis")
                    if type(weight) is not int or not 0 < weight <= MAX_I64:
                        raise ValueError("edge weights must be positive signed 64-bit integers")
                    mass += weight
                    if mass > MAX_I64:
                        raise OverflowError("source row mass exceeds the signed 64-bit bound")
                    stream.write(EDGE.pack(target_sector, weight))
                previous_source = source
                count += 1
            if count != header["record_count"]:
                raise ValueError("record_count does not match the source records")
        os.link(temporary, target)
        temporary.unlink()
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _read_exact(stream: BinaryIO, count: int) -> bytes:
    data = stream.read(count)
    if len(data) != count:
        raise ValueError("truncated profile-census packet")
    return data


def read_header(stream: BinaryIO) -> dict:
    magic, header_length = HEADER_PREFIX.unpack(_read_exact(stream, HEADER_PREFIX.size))
    if magic != MAGIC or not 0 < header_length <= 1_000_000:
        raise ValueError("invalid profile-census packet preamble")
    raw_header = _read_exact(stream, header_length)

    def reject_duplicate_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON header key: {key}")
            result[key] = value
        return result

    header = json.loads(raw_header, object_pairs_hook=reject_duplicate_keys)
    if not isinstance(header, dict):
        raise ValueError("profile-census header must be an object")
    _validate_header(header)
    if raw_header != canonical_bytes(header):
        raise ValueError("profile-census header is not canonically encoded")
    return header


def iter_records(stream: BinaryIO, header: dict) -> Iterator[dict]:
    previous_source = -1
    sector_count = len(header["sector_labels"])
    for _ in range(header["record_count"]):
        source, source_sector, sign, edge_count = ROW_PREFIX.unpack(
            _read_exact(stream, ROW_PREFIX.size)
        )
        if source > MAX_I64 or source <= previous_source:
            raise ValueError("source_id values must be increasing signed 64-bit integers")
        if source_sector >= sector_count or sign not in (-1, 1) or edge_count == 0:
            raise ValueError("invalid source record")
        edges = []
        mass = 0
        for _ in range(edge_count):
            target_sector, weight = EDGE.unpack(_read_exact(stream, EDGE.size))
            if target_sector >= sector_count or not 0 < weight <= MAX_I64:
                raise ValueError("invalid edge record")
            mass += weight
            if mass > MAX_I64:
                raise OverflowError("source row mass exceeds the signed 64-bit bound")
            edges.append((target_sector, weight))
        previous_source = source
        yield {
            "source_id": source,
            "source_sector": source_sector,
            "sign": sign,
            "edges": edges,
        }


def ensure_eof(stream: BinaryIO) -> None:
    if stream.read(1):
        raise ValueError("trailing bytes after profile-census records")
