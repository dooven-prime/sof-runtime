from __future__ import annotations

import hashlib
import json
import unicodedata
from pathlib import Path
from typing import Any


MIN_CANONICAL_INTEGER = -(2**63)
MAX_CANONICAL_INTEGER = 2**63 - 1


def _validate_canonical_value(value: Any, path: str = "<root>") -> None:
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int):
        if not MIN_CANONICAL_INTEGER <= value <= MAX_CANONICAL_INTEGER:
            raise ValueError(f"{path}: integer is outside the signed 64-bit canonical range")
        return
    if isinstance(value, float):
        raise ValueError(
            f"{path}: binary floating-point values are forbidden by sof-cjson-v1"
        )
    if isinstance(value, str):
        if unicodedata.normalize("NFC", value) != value:
            raise ValueError(f"{path}: string is not Unicode NFC")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_canonical_value(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path}: object key is not a string")
            if unicodedata.normalize("NFC", key) != key:
                raise ValueError(f"{path}: object key {key!r} is not Unicode NFC")
            _validate_canonical_value(item, f"{path}.{key}")
        return
    raise ValueError(f"{path}: unsupported canonical JSON type {type(value).__name__}")


def canonical_json_bytes(payload: Any) -> bytes:
    _validate_canonical_value(payload)
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
