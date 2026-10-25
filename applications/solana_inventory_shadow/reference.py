"""Separate Python byte/type/handle reference; never calls the Rust library."""
import ctypes as c
from ctypes import wintypes as w
import hashlib
import json
import os
from pathlib import Path
import struct

SCHEMA = "sof-runtime.a0-flat-inventory.v0"
CODEC = "ascii-json-u64.v0"


class Failure(ValueError):
    def __init__(self, code, detail="", incomplete=False):
        super().__init__(detail); self.code = code; self.incomplete = incomplete


def need(ok, code, detail="", incomplete=False):
    if not ok: raise Failure(code, detail, incomplete)


def encode(value):
    def check(x):
        if x is None or type(x) is bool: return
        if type(x) is int:
            need(0 <= x < 2**64, "CODEC"); return
        if type(x) is str:
            need(all(32 <= ord(a) <= 126 for a in x), "CODEC"); return
        if type(x) is list:
            for a in x: check(a)
            return
        if type(x) is dict:
            for k, v in x.items(): need(type(k) is str, "CODEC"); check(k); check(v)
            return
        raise Failure("CODEC", "unsupported type")
    check(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("ascii")


def decode(raw):
    def unique(pairs):
        out = {}
        for k, v in pairs: need(k not in out, "CODEC", "duplicate key"); out[k] = v
        return out
    def number(s):
        need(not s.startswith("-"), "CODEC"); n = int(s); need(n < 2**64, "CODEC"); return n
    def no_float(s): raise Failure("CODEC", "float/nonfinite")
    try: value = json.loads(raw, object_pairs_hook=unique, parse_int=number, parse_float=no_float, parse_constant=no_float)
    except (json.JSONDecodeError, UnicodeError) as e: raise Failure("CODEC", str(e)) from e
    need(encode(value) == raw, "NONCANONICAL")
    return value


def device(name):
    base = name.split(".")[0].upper()
    return base in {"CON", "PRN", "AUX", "NUL", "CLOCK$", "CONIN$", "CONOUT$"} or (len(base) == 4 and base[:3] in {"COM", "LPT"} and base[3] in "123456789")


def name_ok(name):
    need(type(name) is str and 0 < len(name) <= 255 and name not in (".", "..") and not name.endswith(".")
         and name.isascii() and all(a.isalnum() or a in "._-" for a in name) and not device(name), "NAME")


def key(path):
    value = str(path).removeprefix("\\\\?\\")
    need(value.isascii() and len(value) >= 3 and value[0].isalpha() and value[1:3] == ":\\" and "/" not in value and len(value) <= 16000, "ROOT_PATH")
    for part in value[3:].split("\\"):
        if not part and len(value) == 3: continue
        need(bool(part) and part not in (".", "..") and not part.endswith((".", " "))
             and not device(part) and not any(ord(a) < 32 or a in '/:*?"<>|' for a in part), "ROOT_PATH")
    return value.lower()


def within(path, root):
    p, r = key(path), key(root)
    return p == r or p.startswith(r.rstrip("\\")+"\\")


if os.name == "nt":
    K = c.WinDLL("kernel32", use_last_error=True)
    class Time(c.Structure): _fields_ = [("lo", w.DWORD), ("hi", w.DWORD)]
    class Info(c.Structure):
        _fields_ = [("attrs", w.DWORD), ("created", Time), ("accessed", Time), ("written", Time), ("volume", w.DWORD),
                    ("size_hi", w.DWORD), ("size_lo", w.DWORD), ("links", w.DWORD), ("id_hi", w.DWORD), ("id_lo", w.DWORD)]
    K.CreateFileW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, c.c_void_p, w.DWORD, w.DWORD, w.HANDLE]; K.CreateFileW.restype = w.HANDLE
    K.GetFileInformationByHandle.argtypes = [w.HANDLE, c.POINTER(Info)]; K.GetFileInformationByHandle.restype = w.BOOL
    K.GetFileInformationByHandleEx.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD]; K.GetFileInformationByHandleEx.restype = w.BOOL
    K.GetFinalPathNameByHandleW.argtypes = [w.HANDLE, w.LPWSTR, w.DWORD, w.DWORD]; K.GetFinalPathNameByHandleW.restype = w.DWORD
    K.GetVolumeInformationByHandleW.argtypes = [w.HANDLE, w.LPWSTR, w.DWORD, c.POINTER(w.DWORD), c.POINTER(w.DWORD), c.POINTER(w.DWORD), w.LPWSTR, w.DWORD]
    K.GetVolumeInformationByHandleW.restype = w.BOOL
    K.ReadFile.argtypes = [w.HANDLE, c.c_void_p, w.DWORD, c.POINTER(w.DWORD), c.c_void_p]; K.ReadFile.restype = w.BOOL
    K.SetFilePointerEx.argtypes = [w.HANDLE, c.c_longlong, c.c_void_p, w.DWORD]; K.SetFilePointerEx.restype = w.BOOL
    K.CloseHandle.argtypes = [w.HANDLE]; K.CloseHandle.restype = w.BOOL


def api(ok, code="OS_METADATA"):
    if not ok: raise Failure(code, str(c.get_last_error()), True)


class Handle:
    def __init__(self, path, directory=False):
        need(os.name == "nt", "UNSUPPORTED_PLATFORM", incomplete=True)
        self.path, self.directory, self.h = Path(path), directory, None
        key(path)
        self.h = K.CreateFileW("\\\\?\\"+str(path).removeprefix("\\\\?\\"), 0x80000000, 7, None, 3, 0x02200000, None)
        if self.h == c.c_void_p(-1).value: self.h = None; raise Failure("OS_METADATA", str(c.get_last_error()), True)
        self.stamp()
        buf = c.create_unicode_buffer(32768); n = K.GetFinalPathNameByHandleW(self.h, buf, len(buf), 0)
        api(0 < n < len(buf))
        need(key(buf.value) == key(path), "PATH_ALIAS")

    def close(self):
        if self.h is not None: K.CloseHandle(self.h); self.h = None

    def __del__(self): self.close()

    def ntfs(self):
        buf = c.create_unicode_buffer(64); flags = w.DWORD()
        api(K.GetVolumeInformationByHandleW(self.h, None, 0, None, None, c.byref(flags), buf, len(buf)))
        need(buf.value == "NTFS" and flags.value & 0x40000, "UNSUPPORTED_FILESYSTEM", incomplete=True)

    def streams(self):
        aligned = (c.c_uint64*8192)()
        if not K.GetFileInformationByHandleEx(self.h, 7, aligned, c.sizeof(aligned)):
            if self.directory and c.get_last_error() == 38: return []
            raise Failure("STREAM_METADATA", str(c.get_last_error()), True)
        raw = bytes(aligned); offset = 0; out = []
        while True:
            need(offset+24 <= len(raw), "STREAM_METADATA", incomplete=True)
            nxt, length, size, _ = struct.unpack_from("<IIqq", raw, offset)
            need(length > 0 and length % 2 == 0 and offset+24+length <= len(raw) and size >= 0 and len(out) <= 256, "STREAM_METADATA", incomplete=True)
            try: name = raw[offset+24:offset+24+length].decode("utf-16-le")
            except UnicodeError as e: raise Failure("STREAM_METADATA", str(e), True) from e
            out.append([name, size])
            if nxt == 0: break
            need(nxt % 8 == 0 and nxt >= 24+length, "STREAM_METADATA", incomplete=True); offset += nxt
        return sorted(out)

    def stamp(self):
        i = Info(); api(K.GetFileInformationByHandle(self.h, c.byref(i)))
        need(not i.attrs & 0x400, "REPARSE_POINT")
        need(bool(i.attrs & 0x10) == self.directory and not i.attrs & 0x40, "FILE_TYPE")
        need(self.directory or i.links == 1, "HARD_LINK")
        streams = self.streams()
        need(all(n == "::$DATA" for n, _ in streams) and (self.directory or len(streams) == 1), "NAMED_STREAM")
        length = (i.size_hi << 32)|i.size_lo
        need(self.directory or streams[0][1] == length, "INPUT_CHANGED", incomplete=True)
        return dict(volume=i.volume, file_id=(i.id_hi << 32)|i.id_lo, length=length, links=i.links, attributes=i.attrs,
                    created=(i.created.hi << 32)|i.created.lo, written=(i.written.hi << 32)|i.written.lo, streams=streams)

    def read(self, limit):
        api(K.SetFilePointerEx(self.h, 0, None, 0), "READ"); out = bytearray(); buf = c.create_string_buffer(65536)
        while True:
            n = w.DWORD(); api(K.ReadFile(self.h, buf, len(buf), c.byref(n), None), "READ")
            if not n.value: return bytes(out)
            out.extend(buf.raw[:n.value]); need(len(out) <= limit, "INPUT_CHANGED", incomplete=True)

    def unchanged(self, before):
        try:
            now = self.stamp(); current = Handle(self.path, self.directory)
            try: need(now == before == current.stamp(), "INPUT_CHANGED", incomplete=True)
            finally: current.close()
        except Failure as e: raise Failure("INPUT_CHANGED", str(e), True) from e


class Chain:
    def __init__(self, root):
        self.items = []; key(root)
        for path in list(Path(root).parents)[::-1]+[Path(root)]:
            h = Handle(path, True); self.items.append((h, h.stamp()))
        self.items[-1][0].ntfs()

    def close(self):
        for h, _ in self.items: h.close()

    def __del__(self): self.close()

    def unchanged(self):
        for h, before in self.items:
            other = Handle(h.path, True)
            try:
                for stamp in (h.stamp(), other.stamp()):
                    need((stamp["volume"], stamp["file_id"]) == (before["volume"], before["file_id"]), "INPUT_CHANGED", incomplete=True)
            finally: other.close()


def membership(root):
    names = sorted(p.name for p in Path(root).iterdir()); seen = set()
    need(len(names) <= 4096, "RESOURCE_LIMIT", incomplete=True)
    for name in names:
        name_ok(name); need(name.lower() not in seen, "NAME_ALIAS"); seen.add(name.lower())
    return names


def declarations(raw, expected):
    m, b = decode(raw), decode(expected)
    need(type(m) is dict and type(b) is dict and set(m) == {"schema", "codec", "declarations", "entries"} and set(b) == {"schema", "manifest_schema", "codec", "declarations"}, "DECLARATION")
    need(m["schema"] == b["manifest_schema"] == SCHEMA and m["codec"] == b["codec"] == CODEC
         and b["schema"] == "sof-runtime.a0-inspection-bindings.v0", "VERSION")
    need(m["declarations"] == b["declarations"], "BINDING_MISMATCH")
    d = m["declarations"]; need(type(d) is dict and set(d) == {"producer", "identities", "schemas"}, "DECLARATION")
    need(type(d["producer"]) is dict and set(d["producer"]) == {"id", "version", "executable_sha256"}
         and all(type(d["producer"][f]) is str and d["producer"][f] for f in ("id", "version")), "DECLARATION")
    def digest(x): need(type(x) is str and len(x) == 64 and all(a in "0123456789abcdef" for a in x), "DECLARATION")
    digest(d["producer"]["executable_sha256"])
    need(type(d["identities"]) is dict and set(d["identities"]) == {"source", "execution", "checkpoint"}, "DECLARATION")
    for name, role in (("source", "SourceIdentity"), ("execution", "ExecutionIdentity"), ("checkpoint", "CheckpointIdentity")):
        v = d["identities"][name]; need(type(v) is dict and set(v) == {"role", "sha256"} and v["role"] == role, "DECLARATION"); digest(v["sha256"])
    roles = []; need(type(d["schemas"]) is list, "SCHEMA_BINDING")
    for s in d["schemas"]:
        need(type(s) is dict and set(s) == {"role", "id", "version"}
             and all(type(s[f]) is str and s[f] for f in ("role", "id", "version")), "SCHEMA_BINDING"); roles.append(s["role"])
    need(roles == sorted(set(roles)), "SCHEMA_BINDING")
    names = []; total = 0
    need(type(m["entries"]) is list and len(m["entries"]) <= 4096, "RESOURCE_LIMIT", incomplete=True)
    for e in m["entries"]:
        need(type(e) is dict and set(e) == {"name", "kind", "byte_length", "sha256"} and e["kind"] == "RegularFile" and type(e["byte_length"]) is int, "DECLARATION")
        name_ok(e["name"]); digest(e["sha256"]); names.append(e["name"]); total += e["byte_length"]
    need(names == sorted(set(names)) and len({x.lower() for x in names}) == len(names), "ENTRY_ORDER_OR_ALIAS")
    need(total <= 536870912, "RESOURCE_LIMIT", incomplete=True)
    return m


def inspect(root, manifest, bindings):
    held = []; chains = []
    try:
        root, manifest, bindings = map(Path, (root, manifest, bindings))
        need(not within(manifest, root) and not within(bindings, root), "CONTROL_INSIDE_ROOT")
        chain = Chain(root); chains.append(chain); rh = Handle(root, True); held.append(rh); root_stamp = rh.stamp()
        controls = []
        for p in (manifest, bindings):
            chains.append(Chain(p.parent)); h = Handle(p); held.append(h); stamp = h.stamp()
            need(stamp["length"] <= 4194304, "RESOURCE_LIMIT", incomplete=True)
            controls.append((h, stamp, h.read(stamp["length"])))
        m = declarations(controls[0][2], controls[1][2]); names = membership(root)
        need(names == [e["name"] for e in m["entries"]], "MEMBERSHIP")
        files = []; ids = set(); observed = []
        for entry in m["entries"]:
            h = Handle(root/entry["name"]); held.append(h); stamp = h.stamp()
            need(stamp["length"] == entry["byte_length"], "LENGTH")
            identity = stamp["volume"], stamp["file_id"]; need(identity not in ids, "FILE_ALIAS"); ids.add(identity)
            files.append((h, stamp)); observed.append({**entry, "sha256": hashlib.sha256(h.read(stamp["length"])).hexdigest()})
        need(membership(root) == names, "INPUT_CHANGED", incomplete=True)
        for (h, stamp), e in zip(files, observed):
            h.unchanged(stamp); need(hashlib.sha256(h.read(stamp["length"])).hexdigest() == e["sha256"], "INPUT_CHANGED", incomplete=True); h.unchanged(stamp)
        for h, stamp, raw in controls:
            h.unchanged(stamp); need(h.read(stamp["length"]) == raw, "INPUT_CHANGED", incomplete=True); h.unchanged(stamp)
        rh.unchanged(root_stamp)
        for chain in chains: chain.unchanged()
        need(observed == m["entries"], "DIGEST_MISMATCH")
        return {"status": "INTEGRITY_MATCHES", "entries": observed, "manifest_utf8": controls[0][2].decode(),
                "manifest_sha256": hashlib.sha256(controls[0][2]).hexdigest(), "bindings_sha256": hashlib.sha256(controls[1][2]).hexdigest(), "byte_passes": 2}
    except Failure as e:
        return {"status": "INCOMPLETE" if e.incomplete else "REJECTED", "code": e.code}
    except OSError as e:
        return {"status": "INCOMPLETE", "code": type(e).__name__}
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        return {"status": "REJECTED", "code": "DECLARATION"}
    finally:
        for h in held: h.close()
        for chain in chains: chain.close()
