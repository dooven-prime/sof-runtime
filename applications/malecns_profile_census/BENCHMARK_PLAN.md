# Full-Carrier Profile Census Baseline

Protocol: `malecns-profile-census-baseline.v1`, fixed before the full run.
This is an offline single-host engineering comparison, not paper evidence
promotion or independent scientific replication.

## Fixed Workload and Correctness

- Source files: exactly the two Paper XVI carrier identities in
  `prepare_input.PUBLISHED_CARRIER`; read-only, with size and SHA-256 checks.
- Source basis: 211,577 nodes; 25,214,058 known-sign edges; all 163,439
  eligible, nonempty known-sign source rows. No source sample or truncation.
- Sector field: `somaSide`; missing labels follow the current preparer.
- Arithmetic: exact positive integer magnitudes, separate source signs,
  checked signed-64-bit row masses, GCD-reduced signatures with source sector.
- Output: complete canonical JSON, including exact class-list SHA-256,
  frequencies as bound by that digest, coordinate separation statistics and
  minimum separating sets. All warmup and measured outputs must coincide.
- Preparation is common to both implementations. It is timed separately and
  is not credited as a Rust speedup. No published carrier or evidence is edited.

## Measurement Protocol

Build Rust in release mode with `--locked` before measurement. Run the five
existing positive/hostile fixture tests plus instrumentation and benchmark
regressions. Keep the kernel serial; set common native thread-count environment
variables to one. Record CPU identity, logical/physical counts, memory,
platform, Python/dependency versions, Rust toolchain, source and binary hashes.
Record CPU affinity, but do not claim exclusive machine reservation.

Prepare the packet once in a separately monitored process. Run one excluded
warmup per implementation. Then run five measured pairs in alternating
Python/Rust and Rust/Python order, never concurrently. Before every child,
read and hash the packet outside its timed interval. This warms the filesystem
cache but does not prove a cold-cache measurement or predecoded residency.

Both implementations run as fresh processes. The process wall interval
includes interpreter/executable startup, input, validation, computation,
serialization, stdout and shutdown. Internal timers report:

1. header decode/validation;
2. streaming row decode/validation/aggregation (fused, not compute-only);
3. exact class statistics, canonical class digest and result construction;
4. final semantic JSON serialization, excluding stdout transfer.

Internal timers exclude startup and must not be substituted for process wall
time. Report all samples, median, minimum and maximum; five samples do not
justify p99 or inferential significance claims. Report whole-process ratios
separately from phase ratios. The Python baseline is the checked streaming
oracle, not SciPy SpMV or the optimized rational producer.

Memory is polled every 10 ms. Report maximum observed RSS and, where exposed,
the OS-reported peak working set observed while the process lives. Neither is
an allocation trace; sampled RSS can miss short peaks. Python/Rust children
are measured separately, not with the controller's cumulative child maximum.
Do not sum peaks from nonconcurrent children into a fictitious peak.

## Limits and Failure Rules

Preparation: 600 seconds and 12 GiB observed child RSS. Each census child:
300 seconds and 4 GiB observed child RSS. Monitoring is cooperative, not a
sandbox or hard address-space limit. The runner terminates and reaps a child
on a limit, nonzero exit, invalid diagnostics or output mismatch; no exact
benchmark success is issued for a partial run. No success requires a preset
speedup threshold. Preserve an existing output directory rather than overwrite.

Bind the packet and implementation sources before and after the run, the
protocol bytes, build/toolchain and result digests. Save a compact receipt and
one canonical semantic result. Large input packets and raw per-attempt files
remain under ignored `runs/`; a compact result may be deliberately retained
with a readout. Source artifacts are externally located by their pinned
identities, not by a machine-specific path in the compact receipt.

## Explicit Nonclaims

This baseline does not measure true cold-cache I/O, a persistent worker,
predecoded compute-only throughput, parallel scaling, distributed execution,
`Y^T x`, exact rational dynamics, Solana processing, plugin ABI performance,
recovery, exactly-once delivery or production SLOs. Its performance result is
limited to the supplied packet, serial implementations and recorded machine.
