# Full-Carrier Serial Baseline

Date: 2026-10-23. Status: `PASS_EXACT_BENCHMARK`, a local engineering result.
Protocol: [baseline v1](BENCHMARK_PLAN.md). This does not promote a SOF carrier,
change Paper XVI/XVII, or constitute independent scientific validation.

## Exact Domain and Output

The input uses the release-anchored 312,341,374-byte carrier edges and
3,008,738-byte node table. Their SHA-256 identities are bound in the
[compact receipt](results/full-carrier-somaside.v1/benchmark.v1.json).
The complete declared domain contains 211,577 nodes, 25,214,058 known-sign
edges and all 163,439 eligible nonempty known-sign source rows. Unknown-sign
edges and ineligible rows are outside this workload, not sampled omissions.
The sectorization is `somaSide`, with labels `<missing>, L, M, R`.

The prepared streaming packet is 254,592,750 bytes, SHA-256
`b23d2c7a75f3c57cb9635bef28fd418a21998e97ad94f5cba79a553367ec6c32`.
Both implementations produced 90,148 exact source-sector/profile classes.
The complete class/frequency list has SHA-256
`4795a8094fd45a618a57988228446bf972fcbf13369d05363761c0bc9a39b317`.
All 12 canonical outputs (two excluded warmups and ten measured processes)
were identical, including coordinate separation and minimum separating sets.
The retained [semantic result](results/full-carrier-somaside.v1/semantic-result.json)
has canonical-JSON SHA-256
`4b070bfd15d9f094af910b16c429ee886688cdd1a81ab67f166fe3bbc7db853b`.

## Measurements

Windows 11, Intel Core i7-13700H, 14 physical / 20 logical CPUs and about
63.53 GiB total memory. Python 3.13.0; release Rust 1.97.1, Windows MSVC.
Both census paths were serial. Native thread-count variables were set to one;
the machine was shared, not exclusively reserved or pinned to one core.
Complete environment and source/binary identities are in the receipt.

Every measured process was preceded by an untimed read/hash of the packet.
The operating-system file cache was therefore warmed; it was not flushed.
This is a fresh-process streaming comparison, not a cold-cache or persistent,
predecoded-data-resident benchmark. Five pairs alternated execution order.

| Interval | Python median | Rust median |
|---|---:|---:|
| Whole process | 10.059674 s | 0.532371 s |
| Header decode/validation | 0.000237 s | 0.000153 s |
| Streaming decode/validation/aggregation | 7.673259 s | 0.401468 s |
| Class statistics, digest and report construction | 2.295050 s | 0.094191 s |
| Final semantic JSON serialization | 0.000061 s | 0.000007 s |

Whole-process ranges were 10.011804--10.165806 seconds for Python and
0.497773--0.540654 seconds for Rust. The ratio of median process wall times
was **18.896**. That ratio includes startup, streaming input, checks,
computation, serialization and shutdown; it is not an arithmetic-kernel-only
ratio. Medians of phases need not sum to the median of whole-process time.
All individual samples, not only their summaries, are retained.

The maximum OS-reported peak working set observed during the five measured
processes was 87.76 MiB for Python and 27.97 MiB for Rust. Maximum sampled
RSS was 87.41 MiB and 26.96 MiB, respectively. The monitor requested 10 ms
polls; actual scheduling can delay them. Sampled memory can miss short peaks
and is not an allocation trace. These are separate nonconcurrent process
measurements, not a sum of unrelated process peaks.

Common preparation took **15.335 seconds**, with a maximum observed working
set of **1.768 GiB**. It includes release-byte verification, NPZ/Parquet load,
CSR preparation and checked binary packet generation. This one-time cost is
outside both census intervals and is not counted as a Rust saving. Build and
input-prefetch costs are also outside the measured process intervals.
In particular, 18.896 is not the speedup of a one-off NPZ-to-final-result
pipeline: its shared 15.335-second preparation has not been accelerated.

## Interpretation and Next Gate

The declared exact integer-profile workload now has a full-domain Rust/Python
parity result and a measured serial baseline. Ten fixture/instrumentation/
benchmark-control tests pass in normal and assertions-disabled Python modes;
the tests include unchanged semantic output under instrumentation, rejected
truncation/trailing data/overflow, incomplete diagnostic counts, and bounded
child-process termination. Local binding checks also confirmed the unchanged
packet, source and binary digests after the run.

This result supports continuing the Rust hot-path approach for this workload.
It does not show that Rust universally provides this ratio, that a SciPy or
vectorized baseline has the same ratio, or that parallelization is necessary.
No p99, significance, production SLO, distributed scaling, Solana performance,
or biological conclusion is inferred from five pairs on one shared machine.

The immediate engineering gate is source-addressed reuse of the prepared
packet, with source/policy/format/preparer binding and corrupt-cache rejection.
The measured common preparation dominates a one-off Rust run, so adding
threads first is not justified by this baseline alone. A later exact parallel
profile path needs deterministic global class merging; a signed
sparse-dynamics case needs its own specification. None is silently included
in this baseline. A real
Solana data slice still needs its own source/order/correction/checkpoint
contract; finishing every research-kernel port is not a prerequisite.

The full packet and original per-run files remain under
`runs/malecns-profile-census/full-somaside-baseline-v1/`. The compact receipt
and semantic result are deliberately retained here; no Git commit, public
release, upstream admission or new paper identity is asserted.
