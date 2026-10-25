# Cache Hit Cost Decomposition v1: Local Readout

## Result

Reuse the admitted request, not an unchecked validity decision. On this local
full-carrier run, avoiding repeated Python identity derivation reduced the
five-round median hit from **2.897398 s to 1.657983 s**, while retaining every
v1 Rust execution check. A bounded worker did **not** show a stable additional
benefit: its median was **1.694524 s**. Do not promote a production daemon or
skip packet/source checks on this evidence.

The fixed [plan](CACHE_COST_PLAN_V1.md), [controller](cache_cost_decomposition.py)
and separate [receipt](results/cache-cost.v1/cost-decomposition.v1.json) own this
experiment. The unchanged serial baseline and cache-v1 baseline retain their
own source/binary closures and receipts. All **38** successful consumptions
matched the complete original canonical semantic output, not just its count.
Only `runs/malecns-profile-census/cache-cost-v1-final/` is selected here;
earlier development measurements are not pooled into this receipt.

The workload remains all 163,439 eligible sources and 25,214,058 known-sign
edges, `somaSide`, 90,148 exact classes, and the same 254,592,750-byte packet.
Canonical output SHA-256:
`4b070bfd15d9f094af910b16c429ee886688cdd1a81ab67f166fe3bbc7db853b`.
Packet SHA-256:
`b23d2c7a75f3c57cb9635bef28fd418a21998e97ad94f5cba79a553367ec6c32`.

## Timing Boundaries

Five measured rounds rotate the three modes; one CLI warmup and the worker's
first hit are separately identified. Values below are seconds.

| Complete hit boundary | Minimum | Median | Maximum |
| --- | ---: | ---: | ---: |
| Fresh Python CLI, reconstruct request, fresh Rust | 2.808106 | 2.897398 | 3.040712 |
| Fixed request, fresh Rust, per-call environment check | 1.621398 | 1.657983 | 1.695515 |
| Fixed request, sequential worker, same checks | 1.568415 | 1.694524 | 1.715366 |

The first fresh-process miss was **24.515982 s**, including **5.816513 s** of
identity construction and **16.375466 s** of preparation. This single first-use
sample is retained, not replaced by the faster later identity probes. It is
not an OS-cache-cold disk test. Separate fixed-request admission was
**1.498833 s**; initial worker startup to READY was **0.018898 s**, and its first
full hit was **1.593563 s**.

| Directly timed five-call batch | Fresh Rust | Worker |
| --- | ---: | ---: |
| Already admitted request; includes per-call checks, IPC and output comparisons | 8.141517 | 8.174255 |
| Fresh Python process; includes identity construction, five calls and worker startup/shutdown when applicable | 9.530952 | 9.439273 |

The second row excludes the outer controller's golden-output comparison;
every resulting output was nevertheless checked after timing. These are two
single batch controls, not a latency distribution or a worker speedup claim.
The controller records actual whole-batch, whole-process and round wall times.
No totals here were obtained by adding medians of nested timers.

No-op medians were **0.016265 s** for a fresh probe process and **0.000219 s**
for worker IPC. Their difference did not translate into a stable complete-hit
advantage. The census kernel still starts in a fresh child in both modes.

## Where the Time Goes

Three fresh-process instrumented calls wrap the unchanged identity factory.
Their factory median was **1.110084 s**; whole-process median **1.376561 s**.
Component medians are independently reported and are not additive:

| Identity operation | Median seconds |
| --- | ---: |
| Full edge/node source hashes | 0.265272 |
| PyArrow import | 0.129888 |
| `parquet.read_table` including any deferred import/setup inside that call | 0.525664 |
| Dependency-version reads | 0.028086 |
| Other source/interpreter/consumer hashes | 0.002793 |
| Unassigned conversion, normalization, set/sort and other factory work | 0.169142 |

Small-file digest memoization is not the main opportunity. The useful reuse is
the entire already admitted, deterministic metadata/header/request derivation.
The session still rechecks declared Python/dependency versions on each call
(five-round fresh-Rust median **0.006035 s**), and v1 rechecks source content.
This does not discover new policies or silently follow a changed environment.
Changed desired inputs require readmission and a new identity.

Five isolated Rust probes gave these medians:

| Isolated diagnostic | Seconds |
| --- | ---: |
| v1 source/preparer verification | 0.213704 |
| Packet SHA-256 only | 0.175590 |
| Complete v1 entry validation: manifest, full SHA, full structure | 0.380858 |

These are extra repeated reads, not disjoint slices of one execution. In
particular, subtracting their medians does not measure exact parsing cost.
Actual fresh-Rust hit phase medians included **0.335826 s** initial entry
validation, **0.551583 s** census child, and **0.542183 s** combined final
packet/source verification. These timers nest inside the whole call.

## Reuse and Consumption Boundary

| Work or fact | Current decision |
| --- | --- |
| Policy, expected header, deterministic metadata derivation | Reuse the exact fixed admitted request; do not reinterpret it as a new current-policy query. |
| Source content identity | Still fully hash before and after every v1 call. No size/mtime shortcut. |
| Preparer sources/interpreter and consumer executable | Preserve v1 checks; no persistent validity assumption. |
| Packet manifest, digest, structure and post-consumption stability | Preserve all v1 checks on every call. No validation credential is implemented. |
| Process residency | Bounded measurement probe only; not enough benefit here to justify service promotion. |

A factory-driven v1 hit reads source content three times: Python identity
construction plus Rust pre/post checks. Reusing the request removes the first
pass; it does not remove the two Rust passes. Packet reading is unchanged:
pre-hash, pre-structure, census, post-hash and post-structure, or five complete
logical reads. This is an application-level read count, not physical disk I/O.

There is a conditional route to reusing structural validation. Let a trusted
validator at version `v` validate exact bytes `b` under header/policy `h` and
retain a credential binding `(v, h, length(b), SHA256(b), valid)`. If consumption
re-establishes those same bytes, the deterministic structural result can be
reused (with the usual SHA-256 collision-resistance assumption when a digest
stands for equality). The credential's authority must itself be protected;
a mutable manifest next to a mutable packet is not self-authenticating proof
that validation occurred. A new validator/header/policy requires revalidation.

This would not authorize consuming a different later pathname resolution or
skipping byte verification. Avoiding that recheck requires an enforced
immutable/owned snapshot or equivalent lifetime contract, absent here.
A cooperating cache lock alone does not exclude arbitrary external writers,
and worker survival says nothing about unchanged file contents. Fusing hash
and structural reads is another possible implementation change, but has not
been measured or substituted for v1 here. These are conditional optimization
boundaries, not lower bounds proving v1's number of passes universally minimal.

## Checks and Non-Claims

The 33 focused Python tests pass normally and with `-O`, including 11 new
worker/cost controls: reference parity, five-call request reuse, unchanged
size/mtime corruption rejection, preparer/consumer checks, restart, framing,
64-request limit, EOF and timeout/reaping. The original cache lifecycle and
serial parity controls remain included. The Rust probe also replays the
included reference's identity-key unit test. This is local implementation
evidence, not independent scientific validation or a clean-checkout release.

The worker imports v1 source unchanged, holds no validation credentials across
calls, and retains v1 locking, fresh consumer execution and final checks.
Normal per-call rejection grants no authority to a later request. Its bounded
JSONL lifecycle is documented in the [probe README](../../plugins/rust/cache-cost-probe/README.md).
There is no network service, async queue, authenticated credential, power-loss
guarantee, adversarial-writer defense, general descendant cancellation,
resident-kernel benchmark or Solana workload. The shared machine is not
reserved; small timing differences should not be interpreted as stable gains.
