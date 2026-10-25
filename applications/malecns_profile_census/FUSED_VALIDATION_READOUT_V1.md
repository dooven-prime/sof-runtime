# Packet Hash/Parse Fusion v1: Local Readout

## Result and Scope

The candidate preserves the declared acceptance checks and reduces packet
validation from two complete reads to one. A complete hit still validates
before and after the original serial census: validation reads fall from
**4 to 2**, or **5 to 3 logical packet reads** including the census.
All **13** complete census outputs matched the unchanged serial golden JSON.

On this shared machine, complete-hit process-wall median was
**1.922446 s reference versus 1.819191 s fused**, about 5.4% lower in this run.
This is a modest local result, not a throughput guarantee. Isolated validation
process-wall medians were nearly equal. Whole-hit peak root memory did not
meaningfully improve. Preserve these limits alongside the read reduction.

The fixed [plan](FUSED_VALIDATION_PLAN_V1.md),
[controller](fused_validation_benchmark.py), [Rust experiment](../../plugins/rust/packet-validation-fusion/README.md)
and [receipt](results/packet-fusion.v1/fusion-benchmark.v1.json) own this run.
Previous serial, cache-v1 and cost-decomposition source/binary closures and
receipts are unchanged. This does not change the default cache-v1 executable.

The domain remains `somaSide`, all 163,439 eligible known-sign source rows,
25,214,058 edges, 90,148 exact classes and the same 254,592,750-byte packet.
The canonical output SHA-256 is
`4b070bfd15d9f094af910b16c429ee886688cdd1a81ab67f166fe3bbc7db853b`;
packet SHA-256 is
`b23d2c7a75f3c57cb9635bef28fd418a21998e97ad94f5cba79a553367ec6c32`.

## Why Accepted Records Are Unchanged

For a stable regular file with byte string `b`, the reference computes its
full digest/length, then runs the parser. Fusion runs a hashing reader below
the same default buffered parser. After every successful underlying read,
the hashing state equals SHA-256 over exactly the returned prefix, and its
length counter equals that prefix's length.

The parser predicates are extracted from the SHA-pinned reference's Rust AST,
not separately reimplemented. They retain magic, bounded canonical header,
identity/header equality, row ordering and bounds, signs, sectors, positive
weights, checked mass, complete counts and EOF. A successful EOF check leaves
no unparsed buffered tail and exhausts `b`. Thus the fused result has the same
parsed header/counts and exactly `length(b), SHA256(b)` as the reference.
Rejected input returns no accepted packet record or reusable credential.

All cache execution code outside this validator is retained: source/preparer
verification, policy and format checks, per-key locking, staging/publication,
consumer executable checks, and post-consumption entry/source checks. The
final entry validation compares the packet against the manifest again; it is
not replaced by a cached digest or a size/mtime test.

This is equivalence on the declared stable-input/trusted-local domain, not a
claim that either implementation handles malicious change-and-restore races.
Earlier rejection of malformed input is allowed; failure latency and error
precedence under I/O faults need not be identical.

## Measured Costs

Each action has one excluded warmup per mode and five alternating measured
pairs, all fresh processes. Builds and correctness tests are outside timing.
Both modes include the same read-instrumentation framework. These timings
compare the instrumented binaries, not uninstrumented production execution
or pooled historical baseline samples.
Identity admission (**1.200640 s**) and the new-cache preparation workflow
(**16.721152 s**, including **14.796752 s** preparation) are separate setup
measurements, not part of hit ratios. No worker or buffer-size sweep is used.

| Isolated full-entry validation | Reference | Fused |
| --- | ---: | ---: |
| Packet opens / complete byte passes | 2 | 1 |
| Packet bytes returned | 509,185,500 | 254,592,750 |
| Instrumented `Read` calls, including EOF | 31,324 | 31,080 |
| Process wall median, seconds | 0.465790 | 0.463774 |
| Internal operation wall median, seconds | 0.420862 | 0.411984 |
| Process CPU median, seconds | 0.421875 | 0.390625 |
| Maximum observed root OS peak working set, MiB | 5.156250 | 4.246094 |

| Full hit plus original census | Reference | Fused |
| --- | ---: | ---: |
| Packet validation opens / complete byte passes | 4 | 2 |
| Packet validation bytes returned | 1,018,371,000 | 509,185,500 |
| Instrumented validation `Read` calls, including EOF | 62,648 | 62,160 |
| Additional census logical read | 1 | 1 |
| Process wall median, seconds | 1.922446 | 1.819191 |
| Cache-process CPU median, excludes child, seconds | 1.296875 | 1.187500 |
| Maximum observed root OS peak working set, MiB | 5.738281 | 5.757813 |
| Median sampled peak process-tree RSS, MiB | 30.011719 | 28.312500 |

The read counters observe validation opens and returned bytes, not physical
storage traffic. The census pass is justified separately by complete consumed
record/edge counts; its I/O is not instrumented. Manifest and request reads
are outside these counters. Source-content counters confirm two full reads
per source on every successful complete hit, preserving pre/post checks.

CPU is queried independently using
[Windows GetProcessTimes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes),
summing the measured process's thread user/kernel times, not the census child's
CPU. It is not whole-workflow CPU or wall time. Internal validation intervals
nest inside operation/process timings; their medians must not be added.

The parent samples root/tree memory with a requested 5 ms interval and also
records the root's OS-maintained peak-working-set observations. Sampling can
miss short-lived peaks; tree memory is a simultaneous sample, not a sum of
independent process maxima. The isolated validator avoids the separate 1 MiB
hash buffer, but whole-cache source hashing and the unchanged census remain.
The memory table does not support a general whole-workflow memory reduction.

One reference validation process-wall sample was **1.481322 s**; it remains
in the record. Its internal operation was much shorter. This observation is
not attributed to a particular scheduling, startup or parsing mechanism.
The machine was not reserved, OS caches were warm, and no paired confidence
interval, cold-I/O result or scaling law is claimed.

## Hostile Checks and Disposition

The 41 focused Python tests pass normally and with `-O`, including eight new
fusion tests. They compare both modes on truncation, corruption, wrong or
noncanonical headers, trailing data, invalid ordering/sign/sector/weights,
checked overflow and manifest mismatch. Tests update the manifest digest in
structurally invalid cases so a digest mismatch cannot mask missing parser
checks. Same-size/mtime source drift is still rejected before consumption.

Actual fault consumers mutate a source, damage a packet, or change a positive
weight while leaving the packet structurally valid. All are rejected by the
retained final checks. The valid-weight case passes the second structural
parse and fails its manifest digest comparison. Explicit rebuild and same-key
publication locking also pass. Original lifecycle/parity and cost-probe tests
remain in the focused suite.

Four Rust tests pass: the inherited identity-key control, hashing short/empty
reads, every truncation prefix and single-byte mutation of a small packet,
and multi-buffer digest/EOF agreement. Complete payload equality is checked
for all accepted differential cases; a mutated but valid packet is not
incorrectly required to fail a structure-only check.

Retain the fused reader as an implementation candidate and close this narrow
experiment. No further worker tuning, buffer sweep or credential system is
needed before starting the separately specified sparse-operator kernel.
Credentials remain design-only; dropping consumption byte verification still
requires protected authority and an enforced immutable snapshot/lifetime.
These local engineering controls do not establish public-release reproducibility,
scientific adequacy, adversarial filesystem safety, power-loss durability,
Solana performance or a new mathematical result.
