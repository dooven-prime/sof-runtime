"""Fixed real capture correctness gates, then bounded diagnostic measurements."""
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import argparse
import platform
import statistics
import subprocess

from .common import canonical,file_sha,parse,sha
from .reference import load_capture
from .runner import POINTS,ROOT,bindings,build,invoke


def state_identity(directory):
    return {p.name:file_sha(p) for p in sorted(Path(directory).iterdir()) if p.name!="writer.lock"}


def execute(manifest_path,output_dir,failed_capture=None):
    output=Path(output_dir);output.mkdir(parents=True,exist_ok=False);build();closure=bindings()
    started=datetime.now(timezone.utc).isoformat()
    manifest_path=Path(manifest_path).resolve();manifest,manifest_digest,segments=load_capture(manifest_path)
    if manifest["capture_kind"]!="rpc_capture":raise ValueError("this acceptance entry requires a real RPC capture")
    expected=b"".join(s["bytes"] for s in segments);expected_sha=sha(expected)
    (output/"reference.jsonl").write_bytes(expected)
    records=[parse(line) for line in expected.splitlines()];transactions=[r for r in records if r["kind"]=="transaction"]
    capture_files={p.name:file_sha(p) for p in sorted(manifest_path.parent.iterdir())}
    attempts=[]
    def attempt(name,state,pause=None):
        result,process=invoke(manifest_path,state,output,name,pause)
        attempts.append({"name":name,"result":result,"process":process})
        if not pause:
            if result["status"]!="COMPLETED_LOCAL_CAPTURE" or result["projection_sha256"]!=expected_sha:
                raise ValueError(f"incomplete/incorrect projection: {result}")
            if (state/"projection.jsonl").read_bytes()!=expected:raise ValueError("complete projection bytes differ")
        return result
    clean=output/"clean-state";attempt("clean",clean);clean_identity=state_identity(clean)
    attempt("repeat",clean)
    if state_identity(clean)!=clean_identity:raise ValueError("repeat changed committed state")
    independent=output/"second-state";attempt("second-directory",independent)
    if state_identity(independent)!=clean_identity:raise ValueError("fresh state identity differs")
    recoveries=[]
    for point in POINTS:
        slot=segments[-1]["slot"] if "projection" in point else segments[0]["slot"]
        state=output/f"fault-{point}";attempt(f"{point}-kill",state,(point,slot))
        resumed=attempt(f"{point}-resume",state)
        if state_identity(state)!=clean_identity:raise ValueError("recovered checkpoint/segments differ")
        recoveries.append({"point":point,"slot":slot,"projection_sha256":resumed["projection_sha256"],
                           "resumed_from_index":resumed["resumed_from_index"],"adopted":resumed["orphan_segments_adopted"],
                           "complete_state_matches_clean":True})
    # Performance diagnostics begin only after the full normal/repeat/recovery gates.
    performance=[]
    for i in range(5):
        state=output/f"measured-{i}"
        for mode in ("fresh","replay"):
            name=f"measured-{i}-{mode}";attempt(name,state)
            process=attempts[-1]["process"];elapsed=process["process_wall_seconds"]
            performance.append({"mode":mode,"sample":i,"process_wall_seconds":elapsed,
                                "transactions_per_process_second":len(transactions)/elapsed,
                                "max_observed_rss_bytes":process["max_observed_rss_bytes"],
                                "sampled_cpu_seconds_lower_bound":process["sampled_cpu_seconds_lower_bound"]})
    rejected_capture=None
    if failed_capture:
        failed=Path(failed_capture)
        if (failed/"manifest.json").exists():raise ValueError("failed capture was promoted to a manifest")
        errors=[]
        for path in sorted(failed.glob("*.response.json")):
            value=parse(path.read_bytes())
            if "error" in value:errors.append({"file":path.name,"sha256":file_sha(path),"error":value["error"]})
        if not errors:raise ValueError("missing captured rejection")
        rejected_capture={"status":"INCOMPLETE_CAPTURE_REFUSED","manifest_exists":False,"errors":errors,
                          "files":{p.name:file_sha(p) for p in sorted(failed.iterdir())}}
    if bindings()!=closure or {p.name:file_sha(p) for p in sorted(manifest_path.parent.iterdir())}!=capture_files:
        raise ValueError("capture or implementation changed during acceptance")
    if load_capture(manifest_path)[1]!=manifest_digest:raise ValueError("capture changed")
    summary={}
    for mode in ("fresh","replay"):
        sample=[p for p in performance if p["mode"]==mode];wall=[p["process_wall_seconds"] for p in sample]
        summary[mode]={"process_wall_seconds":{"min":min(wall),"median":statistics.median(wall),"max":max(wall)},
                       "observed_rss_peak_bytes":max(p["max_observed_rss_bytes"] or 0 for p in sample)}
    record={"schema":"sof-runtime.solana-offchain.acceptance.v0","status":"PASS_LOCAL_CAPTURE_CONTROLS",
            "started_utc":started,"completed_utc":datetime.now(timezone.utc).isoformat(),
            "environment":{"python":platform.python_version(),"platform":platform.platform(),"machine":platform.machine(),
                           "rustc":subprocess.run(["rustc","--version","--verbose"],capture_output=True,text=True,check=True).stdout.strip(),
                           "cargo":subprocess.run(["cargo","--version"],capture_output=True,text=True,check=True).stdout.strip(),
                           "filesystem_scope":"local same-filesystem replacement; actual process kill, not power-loss"},
            "capture":{"source":manifest["source"],"manifest_sha256":manifest_digest,"files":capture_files,
                       "server_version_observed_at_capture":manifest["server_version"],"genesis":manifest["genesis"],
                       "range":[manifest["start_slot"],manifest["end_slot"]],"commitment":"finalized",
                       "transaction_versions":dict(Counter(str(tx["version"]) for tx in transactions)),
                       "transactions_with_loaded_addresses":sum(bool(tx["loaded_writable"] or tx["loaded_readonly"]) for tx in transactions)},
            "projection":{"sha256":expected_sha,"bytes":len(expected),"records":len(records),"transactions":len(transactions),
                          "slots":len(segments),"all_python_rust_bytes_equal":True},
            "implementation_sha256":closure,"attempts":attempts,"recoveries":recoveries,
            "correctness_gates_before_measurements":True,"performance_diagnostics":performance,"summary":summary,
            "rejected_recent_capture":rejected_capture,
            "boundary":{"public_complete_replay_package":False,"independent_finality_verification":False,
                        "provider_completeness_verified":False,"power_loss_durability":False,"external_sink_exactly_once":False,
                        "production_throughput_claim":False,"cold_cache_claim":False,"tail_latency_claim":False,
                        "live_streaming":False,"distributed_execution":False,"sof_admission":False}}
    record["files"]={p.relative_to(output).as_posix():file_sha(p) for p in sorted(output.rglob("*")) if p.is_file()}
    with (output/"acceptance.v0.json").open("xb") as stream:stream.write(canonical(record))
    return record


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("manifest",type=Path)
    parser.add_argument("--output-dir",required=True,type=Path);parser.add_argument("--failed-capture",type=Path)
    args=parser.parse_args();r=execute(args.manifest,args.output_dir,args.failed_capture)
    print(canonical({"status":r["status"],"transactions":r["projection"]["transactions"],"recoveries":len(r["recoveries"]),"summary":r["summary"]}).decode())
