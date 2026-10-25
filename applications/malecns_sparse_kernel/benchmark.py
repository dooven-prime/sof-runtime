"""Finite local engineering controls, with resident and process costs separate."""
from __future__ import annotations

import os
NATIVE={key:"1" for key in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS","VECLIB_MAXIMUM_THREADS")}
os.environ.update(NATIVE)

import argparse
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
from time import perf_counter,process_time

import numpy as np
import psutil
import scipy

from ..malecns_profile_census.benchmark import machine_identity
from .prepare import load_source,pinned_sources
from .protocol import arrays_from_source,canonical,file_sha,write_packet,read_packet
from .reference import compare,exact_run,numeric_run,source_numeric
from .runner import bindings,build,request,run


def digest(value): return hashlib.sha256(canonical(value)).hexdigest()


def summary(values):
    return {"minimum":min(values),"median":statistics.median(values),"maximum":max(values)}


def amortization(cost,baseline,candidate):
    delta=baseline-candidate
    return {"conversion_seconds":cost,"baseline_seconds_per_action":baseline,
            "candidate_seconds_per_action":candidate,"saving_seconds_per_action":delta,
            "estimated_first_non_slower_action_count":math.ceil(cost/delta) if delta>0 else None,
            "estimate_not_timed_trajectory":True,
            "estimated_totals":[{"actions":n,"baseline_seconds":n*baseline,
                                 "candidate_plus_conversion_seconds":cost+n*candidate} for n in (1,4,16,64,256)]}


def execute(edges,nodes,output):
    output=Path(output); output.mkdir(parents=True,exist_ok=False)
    started_utc=datetime.now(timezone.utc).isoformat()
    build(); closure=bindings()
    prep=perf_counter(); cpu=process_time()
    source,signs,provenance,load_timing=load_source(edges,nodes)
    layout_start=perf_counter(); target,arrays,conversion=arrays_from_source(source,signs)
    layout_seconds=perf_counter()-layout_start
    del target
    before=perf_counter(); packet=output/"target-row.v0.bin"
    header=write_packet(packet,arrays,{"artifacts":provenance,"sign_policy":"paper16-presynaptic-consensus-transmitter-proxy.v1"})
    serialize=perf_counter()-before; before=perf_counter(); packet_digest=file_sha(packet)
    preparation={**load_timing,"target_integer_csr_conversion_seconds":conversion,
                 "target_layout_and_array_materialization_seconds":layout_seconds,
                 "validation_and_packet_write_seconds":serialize,"packet_hash_seconds":perf_counter()-before,
                 "whole_prepare_seconds":perf_counter()-prep,"controller_prepare_cpu_seconds":process_time()-cpu}
    del arrays
    before=perf_counter(); checked_header,checked_arrays=read_packet(packet,packet_digest)
    reference_packet_validation_seconds=perf_counter()-before
    if checked_header!=header: raise ValueError("packet reference mismatch")
    del checked_arrays
    source_y,coefficient_seconds=source_numeric(source,signs); csc=source_y.transpose(copy=False)
    conversion_samples=[]
    for _ in range(5):
        before=perf_counter(); csr=csc.tocsr(copy=True); conversion_samples.append(perf_counter()-before)
    masses=np.asarray(source.sum(axis=1)).ravel()
    seed=int(np.argmax(np.where(signs>0,masses,-1)))
    n=len(signs); onehot=np.zeros(n); onehot[seed]=1
    vectors={"dense_nonnegative_v0":((np.arange(n,dtype=np.int64)*37)%1009)/1009.,"onehot_largest_positive_mass":onehot}
    vector_binding={name:{"canonical_sha256":digest(x.tolist()),"length":n,
                          "onehot_source":seed if name.startswith("onehot") else None} for name,x in vectors.items()}
    observations=[]; amortized=[]; numerical_counter=0
    for name,x in vectors.items():
        for operation in ("spmv","update"):
            scipy_times={"source_transpose_csc":[],"target_csr":[]}; expected=None
            for sample in range(6):
                order=[("source_transpose_csc",csc),("target_csr",csr)]
                if sample%2: order.reverse()
                for layout,matrix in order:
                    before=perf_counter(); value=numeric_run(matrix,x,operation,4); elapsed=perf_counter()-before
                    if sample: scipy_times[layout].append(elapsed)
                    if expected is None: expected=value
                    elif not compare(expected,value)["accepted"]: raise ValueError("SciPy layouts disagree")
            reference_path=output/f"{name}-{operation}.reference.json"
            with reference_path.open("xb") as stream: stream.write(canonical(expected.tolist()))
            scipy_metrics={key:summary([t/4 for t in times]) for key,times in scipy_times.items()}
            serial=None; rust_metrics={}
            order=(1,2,4) if numerical_counter%2==0 else (4,2,1)
            values={}
            for threads in order:
                task=request(packet,packet_digest,x.tolist(),operation=operation,threads=threads,iterations=4,repeats=5,warmups=1)
                result,resource=run(task,output,f"{name}-{operation}-rust-{threads}")
                actual=np.asarray(result["output"],dtype=np.float64); error=compare(expected,actual)
                if not error["accepted"]: raise ValueError(f"numerical mismatch: {error}")
                values[threads]=actual
                per_action=summary([t/4 for t in result["timings"]["kernel_sample_seconds"]])
                rust_metrics[str(threads)]=per_action
                observations.append({"vector":name,"mode":"numerical","operation":operation,"threads":threads,
                                     "error_vs_scipy":error,"resident_seconds_per_action":per_action,
                                     "timings":result["timings"],"resources":resource,
                                     "output_canonical_sha256":digest(result["output"]),"reference_file_sha256":file_sha(reference_path)})
                print(f"{name}/{operation}/Rust-{threads}: max-error={error['max_absolute_error']:.3g}, action={per_action['median']:.6f}s",flush=True)
            serial=values[1]
            if not all(np.array_equal(serial.view(np.uint64),v.view(np.uint64)) for v in values.values()):
                raise ValueError("Rust serial/parallel output is not bitwise equal")
            base=scipy_metrics["source_transpose_csc"]["median"]
            costs={"vector":name,"operation":operation,"scipy_resident_seconds_per_action":scipy_metrics,
                   "layout_only":amortization(statistics.median(conversion_samples),base,scipy_metrics["target_csr"]["median"]),
                   "cross_language_resident_estimate":{}}
            for threads in (1,2,4):
                observed=next(o for o in observations if o["vector"]==name and o["operation"]==operation and o["threads"]==threads)
                rust_setup=observed["timings"]["coefficient_conversion_seconds"]+observed["timings"]["pool_creation_seconds"]
                # Same source decode is common; include the additional persistent target packet creation.
                extra=layout_seconds+serialize+preparation["packet_hash_seconds"]+observed["timings"]["read_hash_decode_validate_seconds"]+rust_setup
                costs["cross_language_resident_estimate"][str(threads)]=amortization(extra,base,rust_metrics[str(threads)]["median"])
            amortized.append(costs); numerical_counter+=1
    exact_vector=[["0","1"] for _ in range(n)]; exact_vector[seed]=["1","1"]
    exact_binding={"canonical_sha256":digest(exact_vector),"onehot_source":seed,"iterations":1}
    for operation in ("spmv","update"):
        before=perf_counter(); cpu=process_time(); expected=exact_run(source,signs,exact_vector,operation,1)
        py_wall=perf_counter()-before; py_cpu=process_time()-cpu
        reference_path=output/f"exact-{operation}.reference.json"
        with reference_path.open("xb") as stream: stream.write(canonical(expected))
        for threads in (1,4):
            result,resource=run(request(packet,packet_digest,exact_vector,"exact",operation,threads),output,f"exact-{operation}-{threads}")
            if result["output"]!=expected: raise ValueError("exact Fraction/Rust mismatch")
            observations.append({"mode":"exact","operation":operation,"threads":threads,"rational_equal_all_coordinates":True,
                                 "reference_seconds":py_wall,"reference_cpu_seconds":py_cpu,
                                 "timings":result["timings"],"resources":resource,
                                 "output_canonical_sha256":digest(result["output"]),"reference_file_sha256":file_sha(reference_path)})
            print(f"exact-onehot/{operation}/Rust-{threads}: all {n} rational coordinates equal",flush=True)
    if pinned_sources(edges,nodes)!=provenance or file_sha(packet)!=packet_digest or bindings()!=closure:
        raise ValueError("carrier, packet or implementation changed")
    process=psutil.Process(); memory=process.memory_info(); times=process.cpu_times()
    record={"schema":"sof-runtime.malecns-spmv.benchmark.v0","status":"PASS_LOCAL_BOUNDED_CONTROLS",
            "started_utc":started_utc,"completed_utc":datetime.now(timezone.utc).isoformat(),"environment":machine_identity(),
            "execution":{"native_thread_environment":NATIVE,"rust_threads":[1,2,4],"warmups":1,"samples":5,
                         "numerical_iterations_per_sample":4,"exact_iterations":1,"exclusive_machine":False},
            "source_artifacts":provenance,"input":{"packet_sha256":packet_digest,"packet_bytes":packet.stat().st_size,
                                                     "n":header["n"],"nnz":header["nnz"]},
            "vectors":vector_binding,"exact_vector":exact_binding,"implementation_sha256":closure,
            "preparation":preparation,"reference_packet_validation_seconds":reference_packet_validation_seconds,
            "scipy_source_coefficient_seconds":coefficient_seconds,"scipy_transpose_csr_conversion_seconds":summary(conversion_samples),
            "observations":observations,"amortization":amortized,
            "controller_resources":{"current_rss_bytes":memory.rss,"os_peak_working_set_bytes":getattr(memory,"peak_wset",None),
                                    "process_cpu_seconds":times.user+times.system,"scope":"controller including reference preparation, excluding Rust children"},
            "boundary":{"paper_evidence_promotion":False,"solana_workload":False,"exact_full_orbit_replay":False,
                        "numerical_is_exact":False,"cold_cache_claim":False,"production_parallel_scaling":False,
                        "all_rust_thread_outputs_bitwise_equal":True,"public_complete_replay_package":False}}
    record["files"]={p.name:file_sha(p) for p in sorted(output.iterdir()) if p.is_file()}
    with (output/"benchmark.v0.json").open("xb") as stream: stream.write(canonical(record))
    return record


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edges",required=True,type=Path); parser.add_argument("--nodes",required=True,type=Path)
    parser.add_argument("--output-dir",required=True,type=Path)
    args=parser.parse_args()
    result=execute(args.edges,args.nodes,args.output_dir)
    print(json.dumps({"status":result["status"],"observations":len(result["observations"])},indent=2))
