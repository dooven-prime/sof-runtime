# Incremental Replay v1: Local Readout

Status: **PASS_LOCAL_INCREMENTAL_CONTROLS**. Incremental work avoidance and
fixed-capture recovery are implemented; an end-to-end speedup is **not**
established. V0 sources/selected receipt, MaleCNS and Q2 identities are unchanged.

## Fixed Data

The plan was written before capture: finalized devnet slots
**378967388--378967451**, inclusive. All 64 were listed and retrieved. No
unsupported data were filtered. The capture contains:

| Coverage | Count |
|---|---:|
| Transactions | 1,381 |
| Legacy / v0 | 1,257 / 124 |
| Failed transactions retained | 40 |
| Transactions with loaded addresses | 55 |
| Loaded writable / readonly addresses | 334 / 461 |

This is larger than v0's 3-slot/79-transaction sample, not a representative
network workload. Raw capture plus metadata totals 2,693,431 bytes. The RPC
server version is bound in the manifest; it is not historical block-producer
version evidence. Finality and provider completeness were not independently
verified. Transaction compatibility remains legacy/v0 only.

The complete Python/Rust projection contains **1,445 records**, **1,994,158
bytes**, SHA-256:

```text
a8053b902e3824651851bd612b741d4358ae5112ff8397ca3ea2cde6770d1f92
```

Capture-manifest SHA-256:

```text
39fa0b60d7ee18f636b5641ffbf727094107fe3e3e42f0e71214128d5ba95424
```

## Correctness and Skipped Work

The selected run has 37 process attempts and 27 completed state directories,
all checked against the full separately implemented Python projection. It
includes three clean runs, complete-state reuse, six actual process-kill
boundaries, and early/middle/late paired resumes. Unit controls ran in both
ordinary and optimized Python modes: nine test methods each, including
negative subcases. The Rust crate also passes the two inherited projection
parser tests; these are not additional incremental-recovery proofs.

At 2/32/62 committed slots, incremental runs decoded exactly **62/32/2**
suffix blocks and **zero** prefix blocks. The full-reproject control decoded
the same suffix plus **2/32/62** prefix blocks. A complete repeated run decoded
zero blocks and published no new slot segments. The incremental decode trap
was enabled in acceptance and independently exercised by a rejecting
full-reproject test.

Prefix raw input, segments, checkpoint frame, external checkpoint anchor,
identity and chain metadata are still checked. Corrupt prefix input/output,
coordinated segment/checkpoint tampering after anchor binding, bad cursor,
foreign identity, absent anchor, path/JSON errors, unsupported versions,
invalid indices, writer conflicts and future orphans do not yield completion.
A matching orphan next segment is uncommitted and gets projected before adoption.

The anchor's provenance matters: it must come from a prior validated run of
this implementation, not from merely hashing an unknown directory. Full
reprojection can establish a fresh local basis. The implementation does not
claim immutable storage, a cryptographic execution attestation or resistance
to a party controlling both state and the trusted anchor.

## Recovery Cost Curves

Three paired repetitions per position, alternating mode order. Values below
are medians in seconds; independent phase medians must not be added as if
they were the phase decomposition of a single invocation.

| Committed slots | Incremental wall | Full-reproject wall | Incremental prefix integrity | Incremental suffix projection | Incremental new commit |
|---:|---:|---:|---:|---:|---:|
| 2 | 0.698 | 0.685 | 0.034 | 0.097 | 0.458 |
| 32 | 1.096 | 1.105 | 0.685 | 0.049 | 0.249 |
| 62 | 1.528 | 1.521 | 1.384 | 0.003 | 0.018 |

The clean-run median was **0.665 s**. Paired wall-time ranges overlap; this
sample does not support a robust speed advantage. The prefix-integrity phase
dominates later cloned-snapshot runs. An immediate complete-state repeat
checked its entire prefix in about 0.019 s, substantially different from the
freshly copied snapshots. Cache/storage/file-state effects were not isolated,
so the observed curve is **not** an intrinsic per-byte verification law.

Each pair starts from byte-identical copies of one actual interrupted state.
Copying is outside the child-process timer; page cache is not forced cold or
warm. The result is a bounded local paired diagnostic, not a disk benchmark.
The receipt retains individual measurements, order, CPU sampling lower bounds
and memory observations, rather than just the medians. The largest observed
OS-reported peak working set among completed child runs was **6,791,168 bytes**;
this is not a worst-case memory bound for larger blocks or captures.

The 62-slot prefix avoided decoding **2,577,584** committed response bytes;
only **60,786** suffix response bytes were decoded. It still verified those
prefix response bytes and **1,940,724** prefix segment bytes, streamed the
complete **1,994,158-byte** output, and rehashed capture input after consumption.
Skipping decoding does not mean skipping integrity or aggregate I/O.

## Saved Closure

Selected compact record: [acceptance.v1.json](results/acceptance.v1.json).
The full local run remains at
`runs/solana-incremental/acceptance-v1-final/`; the raw capture is at
`runs/solana-incremental/capture-devnet-64-v1/`.
The earlier `acceptance-v1/` run is retained but is not the selected record.
The selected receipt binds 2,020 saved files and source/executable identities.
The verifier rechecks those bytes, Python projection, state contents, exact
work traces, measurement/result binding and planned curve inventory.

Verification returned `VERIFIED_LOCAL_SAVED_COMPARISONS`. It did not reexecute
the worker or independently attest the run. The compact record alone is not a
self-contained public replay package; local capture/log/state files are not
bundled. Build/run commands and trust inputs are in [README](README.md).

## Disposition

Freeze this bounded functionality/control result, not a performance claim.
It establishes real suffix-only decoding with explicit prefix integrity and
recovery costs on a larger fixed capture. No live RPC runtime, fork switching,
remote sink, plugin ABI, transaction-version expansion, distributed recovery,
power-loss durability or throughput guarantee follows. Further performance
work should isolate verification/storage costs before expanding architecture.
