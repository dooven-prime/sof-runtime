"""Capture byte identity and confined local JSON utilities."""
import hashlib
import json
import math
from pathlib import Path

SCHEMA="sof-runtime.solana-capture.v0"
PROJECTION="sof-runtime.solana-projection.v0"
CONFIG={"commitment":"finalized","encoding":"json","transactionDetails":"full",
        "maxSupportedTransactionVersion":0,"rewards":False}


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()


def sha(raw): return hashlib.sha256(raw).hexdigest()


def file_sha(path):
    with Path(path).open("rb") as stream: return hashlib.file_digest(stream,"sha256").hexdigest()


def parse(raw):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result: raise ValueError("duplicate JSON key")
            result[key]=value
        return result
    def invalid(value): raise ValueError(f"nonfinite JSON: {value}")
    def finite(value):
        number=float(value)
        if not math.isfinite(number): raise ValueError("nonfinite JSON number")
        return number
    return json.loads(raw,object_pairs_hook=unique,parse_constant=invalid,parse_float=finite)


def confined(root,name):
    if not isinstance(name,str) or not name or any(c in name for c in ("/","\\",":")) or name in (".",".."):
        raise ValueError("nonlocal capture member")
    path=root/name
    if path.is_symlink() or not path.is_file() or path.resolve().parent!=root.resolve():
        raise ValueError("capture member not a confined regular file")
    return path


def response(root,entry):
    if type(entry["id"]) is not int or not 0<=entry["id"]<2**64:
        raise ValueError("RPC ID must be an unsigned integer")
    request_raw=confined(root,entry["request"]).read_bytes(); raw=confined(root,entry["response"]).read_bytes()
    if len(raw)>32*1024**2 or len(request_raw)>65536 or sha(raw)!=entry["response_sha256"] or sha(request_raw)!=entry["request_sha256"]:
        raise ValueError("capture member identity/size mismatch")
    request=parse(request_raw); reply=parse(raw)
    if canonical(request)!=canonical({"jsonrpc":"2.0","id":entry["id"],"method":entry["method"],"params":entry["params"]}):
        raise ValueError("bound RPC request differs")
    if reply.get("jsonrpc")!="2.0" or type(reply.get("id")) is not int or reply["id"]!=entry["id"] or "error" in reply or "result" not in reply:
        raise ValueError("RPC error/envelope mismatch")
    return reply["result"]
