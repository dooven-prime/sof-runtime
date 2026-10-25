# Prepared-Input Cache v1 Readout

Date: 2026-10-23. Status: `PASS_CACHE_BASELINE`, local engineering evidence.
Scope: [the cache contract](PREPARED_INPUT_CACHE_V1.md) and the separately fixed
[measurement plan](CACHE_BENCHMARK_PLAN_V1.md). The earlier full-carrier serial
baseline, its result, code and binary remain unchanged.

## Correctness and Recovery

The retained [receipt](results/prepared-cache.v1/cache-benchmark.v1.json) comes
from the final source-bound run, not a pool of earlier development attempts.
It uses all 163,439 eligible known-sign sources and 25,214,058 known-sign edges
of the same `somaSide` carrier. Every prepared packet has the original
254,592,750-byte length and SHA-256
`b23d2c7a75f3c57cb9635bef28fd418a21998e97ad94f5cba79a553367ec6c32`.
All eight successful executions reproduce the unchanged complete semantic
result, including its 90,148 exact profile classes and class-frequency digest.

The cache identity in this run is
`448e7d1a19a8ed4f3362aee3cfb2f563d5f3ca3b5502689c5f019e5b8757e2a3`.
It binds the original sources, declared policies, packet format and preparer
source/runtime version. It is not the identity of a scientific claim or of a
Solana execution.

The full-carrier sequence verifies a first miss, five hits, rejection after
one-byte damage in this run's cache only, explicit quarantine/rebuild and a
post-rebuild hit. No consumer runs for the rejection. Hits do not prepare the
packet again. Published source files and old results are never damaged.

Twelve cache tests additionally exercise changed source/preparer identity,
key components, malformed protocol/header/manifest, incomplete entries,
failed and source-mutating builds, an actual killed builder invocation,
same-key concurrent processes, bounded lock wait and consumer executable
identity. Interrupted staging is not admitted; after one process publishes,
the competing process validates its entry instead of publishing a second one.
The interruption test separately terminates its orphaned fixture preparer.
This does not claim general descendant cancellation by the cache tool.

## Costs

Every attempt starts a fresh Python CLI, which constructs the identity and
launches the Rust cache process. It then runs the serial Rust census under the
cache lock when valid. Build is excluded. The machine is the same shared
Windows/i7-13700H host as the serial baseline, with no exclusive reservation
or OS cache eviction. The preparer and native thread-count environment remain
fixed. Exact versions, hashes and all individual observations are retained.

| Scenario | Diagnostic | Complete process wall time |
|---|---|---:|
| First preparation and execution | `CACHE_MISS_PREPARED` | 17.245 s |
| Five ordinary hits | `CACHE_HIT_VALIDATED` | median 2.922 s; range 2.840--3.035 s |
| Damaged cache, default policy | `CACHE_INVALID_REJECTED` | 1.666 s |
| Explicit re-preparation and execution | `CACHE_INVALID_REBUILT` | 18.020 s |
| Post-rebuild hit | `CACHE_HIT_VALIDATED` | 2.950 s |

Preparation itself took 14.119 seconds on the miss and 14.610 seconds on the
explicit rebuild. These are two individual observations, not a confidence
interval or a general preparation-time theorem.

Five-hit phase medians were:

| Interval | Median |
|---|---:|
| Python identity construction, including source hashing/metadata | 1.126 s |
| Rust cache process wall time | 1.549 s |
| Initial source/preparer checks inside Rust | 0.197 s |
| Existing packet/manifest validation | 0.314 s |
| Rust census process inside the cache | 0.503 s |
| Final packet/source/preparer checks | 0.521 s |
| Lock wait, uncontended full-carrier run | 0.000119 s |

Nested intervals must not be added together; phase medians also need not sum
to the median of their enclosing interval. Final checks include another full
packet validation and source verification, not merely a timestamp check.
The cache key is source-bound, but a hit is not free. The validated cache
workflow has different obligations from the old census-only baseline, so its
2.922 seconds is not directly comparable as a speedup against the old
0.532-second Rust process interval.

The useful result is elimination of repeated preparation while retaining the
declared integrity and provenance checks. It also shows that request
construction and verification now cost more than the arithmetic/aggregation
consumer. No parallel speedup is assumed or measured.

## Boundaries and Retention

This is a trusted-local-filesystem, forward, process-interruption-tested
protocol. It is not a remote/distributed cache, adversarial filesystem
defense, power-loss guarantee, exactly-once executor or Solana workload.
Quarantine and abandoned staging require separate lifecycle policy; they are
not automatically garbage-collected. The preparer source/dependency binding
is not a hermetic execution proof. Packet integrity does not by itself prove
that an untrusted producer implemented the mathematical preparation rule.

The new run remains under
`runs/malecns-profile-census/cache-baseline-v1-final/`; the compact receipt is
retained separately here. It binds its own contract, controller, Rust source,
tests and binaries and references the unchanged old semantic result. Earlier
development attempts remain separate scratch runs. No paper, SOF contract,
public release identity, independent scientific replication or new theorem
is promoted by this engineering result.
