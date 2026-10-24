# Prefix Integrity Cost Attribution v1

A bounded, read-only attribution experiment over the frozen
[incremental replay v1](../solana_incremental_replay/README.md), not a replay
implementation change. [Plan](plan.v1.json), [contract](CONTRACT.md) and
[readout](READOUT_V1.md) fix its domain, measurements and stop rule.

## Local Commands

From the repository root, with Windows, Rust, Python and `psutil`:

```powershell
cargo build --release --locked --manifest-path plugins/rust/solana-prefix-integrity/Cargo.toml
python -B -m unittest discover -s tests/cross_language -p test_solana_prefix_integrity.py -v
python -B -O -m unittest discover -s tests/cross_language -p test_solana_prefix_integrity.py -v
python -B -m applications.solana_prefix_integrity.experiment runs/solana-incremental/capture-devnet-64-v1/manifest.json runs/solana-prefix-integrity/my-attribution-v1
python -B -O -m applications.solana_prefix_integrity.verify runs/solana-incremental/capture-devnet-64-v1/manifest.json runs/solana-prefix-integrity/my-attribution-v1
```

Use a new output directory. The final two commands require the **exact saved
capture** named in the plan, plus the unchanged v1 executable and selected
v1 receipt. A new RPC capture has a different provenance identity even for
the same historical range. This local procedure is not a self-contained public
dataset package. Offline synthetic controls do not require the real capture.

The selected summary is [attribution-summary.v1.json](results/attribution-summary.v1.json).
The complete local record, per-file timings, before/after file states, stdout,
prefix aggregates and states remain under ignored `runs/`. The verifier checks
saved bytes and a separately implemented full Python projection, not an
independent execution attestation or a physical disk measurement.

## Instrumentation

The Rust probe compiles the unchanged v1 source privately. Its four target
phases are checkpoint/anchor, raw-input hashing, segment validation, and
aggregate streaming. Metadata admission and complete post-consumption hashing
are additional phases. The probe groups input and segment reads separately;
v1 interleaves them. These are measurements of a diagnostic execution with the
same checks, **not a byte-for-byte timing trace of the original executable**.
Aggregation produces only the committed prefix, outside the state directory.
No suffix is decoded and no checkpoint is advanced.

Process user/kernel CPU comes from Windows
[GetProcessTimes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes).
The reported units do not guarantee sub-millisecond measurement accuracy.
Short intervals show quantization, including zero readings or CPU deltas
larger than interval wall time; do not interpret them as precise utilization.
Windows [GetProcessIoCounters](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getprocessiocounters)
accounts for process I/O, not physical disk service. Separately, digest and
stream operations record actual bytes returned by reads and bytes written.
Metadata-admission and total logical-read counts are explicitly unavailable,
because the frozen parser's internal reads are not individually instrumented.

File observations retain sizes, device/inode, times, attributes and reparse
tags. They are diagnostics only. Explicit pre-reading does not certify bytes
or guarantee a particular OS cache state; every measured probe still hashes
all required bytes and validates its externally bound checkpoint.

## Boundaries

Fresh-first and copy-first orders are balanced; read-warmed order alternates.
Fresh does not mean cold. Metadata observations and state preparation happen
outside child timers. Background activity is not fully isolated. Per-file
times are nested inside phase times and must not be added to them.

The result stops this fixed-capture acceleration round. It does not authorize
weaker validation, trust mtime, deploy a cache credential, diagnose a particular
storage/security subsystem, or implement input progression, source correction
or checkpoint invalidation. Those are separate systems-semantics tasks.
