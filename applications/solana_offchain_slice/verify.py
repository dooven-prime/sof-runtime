"""Recheck local capture/state/output closure, not an execution attestation."""
import argparse
from pathlib import Path

from .common import canonical,file_sha,parse,sha
from .reference import load_capture
from .runner import bindings


def verify(manifest_path,directory):
    root=Path(directory).resolve(strict=True);record=parse((root/"acceptance.v0.json").read_bytes())
    if record["status"]!="PASS_LOCAL_CAPTURE_CONTROLS" or record["implementation_sha256"]!=bindings():raise ValueError("receipt/code binding")
    actual={p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    if actual!=set(record["files"])|{"acceptance.v0.json"}:raise ValueError("run inventory differs")
    for name,digest in record["files"].items():
        relative=Path(name)
        if relative.is_absolute() or ".." in relative.parts:raise ValueError("unsafe receipt member")
        path=root/relative
        if any(parent.is_symlink() for parent in [path,*path.parents] if parent!=root.parent):raise ValueError("symlink receipt member")
        if not path.resolve().is_relative_to(root) or file_sha(path)!=digest:raise ValueError("run member integrity")
    manifest_path=Path(manifest_path).resolve();manifest,msha,segments=load_capture(manifest_path)
    captured={p.name:file_sha(p) for p in sorted(manifest_path.parent.iterdir())}
    if msha!=record["capture"]["manifest_sha256"] or captured!=record["capture"]["files"]:raise ValueError("source capture binding")
    expected=b"".join(s["bytes"] for s in segments)
    if sha(expected)!=record["projection"]["sha256"] or (root/"reference.jsonl").read_bytes()!=expected:raise ValueError("reference projection")
    identity={"manifest_sha256":msha,"projection":"sof-runtime.solana-projection.v0","executable_sha256":record["implementation_sha256"]["rust_binary"]}
    committed=[{"slot":s["slot"],"sha256":sha(s["bytes"]),"records":s["records"]} for s in segments]
    states=list(root.glob("*/checkpoint.json"))
    if len(states)!=13:raise ValueError("missing normal/recovery/measured states")
    for checkpoint in states:
        state=checkpoint.parent
        cp={"schema":"sof-runtime.solana-checkpoint.v0","identity":identity,"next_index":len(segments),"committed":committed}
        if canonical(parse(checkpoint.read_bytes()))!=canonical(cp) or canonical(parse((state/"identity.json").read_bytes()))!=canonical(identity):raise ValueError("checkpoint identity/prefix")
        if (state/"projection.jsonl").read_bytes()!=expected:raise ValueError("aggregate projection mismatch")
        for segment in segments:
            if (state/f"slot-{segment['slot']}.jsonl").read_bytes()!=segment["bytes"]:raise ValueError("segment projection mismatch")
    if len(record["recoveries"])!=6 or not all(x["complete_state_matches_clean"] for x in record["recoveries"]):raise ValueError("recovery controls incomplete")
    return {"status":"VERIFIED_LOCAL_SAVED_COMPARISONS","states":len(states),"projection_sha256":sha(expected),
            "worker_reexecuted":False,"independent_validation":False,"independent_finality_verification":False}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("manifest",type=Path);parser.add_argument("directory",type=Path)
    args=parser.parse_args();print(canonical(verify(args.manifest,args.directory)).decode())
