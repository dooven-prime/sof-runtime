"""Inventory of this test's owned fixtures, including intentionally unsafe objects.

This is not the A0 admission inventory: it records junctions without following
them and named streams without admitting them, so hostile evidence cannot vanish
while an ordinary default-stream file hash stays the same.
"""
import ctypes as c
import hashlib
import os
from pathlib import Path
import re

from applications.solana_offchain_slice.common import file_sha
from . import reference as ref


def fixture_streams(path, directory):
    ref.need(os.name == "nt", "UNSUPPORTED_PLATFORM", incomplete=True)
    h = ref.Handle.__new__(ref.Handle)
    h.path, h.directory, h.h = Path(path), directory, None
    h.h = ref.K.CreateFileW("\\\\?\\"+str(path).removeprefix("\\\\?\\"), 0x80000000, 7, None, 3, 0x02200000, None)
    if h.h == c.c_void_p(-1).value:
        h.h = None; raise OSError(c.get_last_error(), "fixture stream metadata unavailable")
    try:
        streams = h.streams(); out = {}
        for name, length in streams:
            if name == "::$DATA": continue
            if not re.fullmatch(r":[A-Za-z0-9._-]+:\$DATA", name) or length > 8*1024**2:
                raise ValueError("unregistered fixture stream form")
            with open(str(path)+name.removesuffix(":$DATA"), "rb") as stream:
                raw = stream.read(length+1)
            if len(raw) != length: raise ValueError("fixture stream changed")
            out[name] = {"length": length, "sha256": hashlib.sha256(raw).hexdigest()}
        return out
    finally: h.close()


def inventory(root, exclude=()):
    root = Path(root).resolve(strict=True); out = {".": {"kind": "Directory", "streams": fixture_streams(root, True)}}
    def walk(directory):
        for p in sorted(directory.iterdir()):
            name = p.relative_to(root).as_posix()
            if name in exclude: continue
            m = p.lstat(); attrs = getattr(m, "st_file_attributes", None)
            if attrs is None: raise ValueError("Windows fixture metadata required")
            if attrs & 0x400:
                target = os.readlink(p)
                if not ref.within(Path(target).resolve(), root): raise ValueError("fixture reparse target escaped its owned run")
                out[name] = {"kind": "ReparsePoint", "target": target}; continue
            if p.is_dir():
                out[name] = {"kind": "Directory", "streams": fixture_streams(p, True)}; walk(p)
            elif p.is_file():
                out[name] = {"kind": "RegularFile", "length": m.st_size, "sha256": file_sha(p),
                             "links": m.st_nlink, "streams": fixture_streams(p, False)}
            else: raise ValueError("unregistered fixture type")
    walk(root)
    return out
