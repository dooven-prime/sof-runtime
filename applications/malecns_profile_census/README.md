# MaleCNS Profile Census Replay Case

This is an offline engineering case for exact profile aggregation over a
source-addressed sparse network. Python prepares the input packet and provides
the reference implementation; a Rust kernel recomputes source-row masses,
positive sector profiles, exact profile classes, and coordinate separation
counts. The two outputs are compared byte-for-byte after canonical JSON
encoding.

For an eligible source row `a`, the kernel computes

```text
s[a] = sum_v |W[a,v]|; the packet stores these edge magnitudes as positive integers
p[a,j] = sum of weights from a to target sector j, when source sign is +1
         0 for every j, when source sign is -1
g[a] = gcd(s[a], p[a,0], ..., p[a,m-1])
profile[a] = (s[a]/g[a], p[a,0]/g[a], ..., p[a,m-1]/g[a])
```

Thus profile equality is tested with exact integer keys, not floating-point
ratios. The source-sector index remains part of the class key. Row sums and
profile coordinates use checked signed-64-bit bounds. Malformed, reordered,
truncated, overflowing, or trailing input fails without emitting a result.
The row sign is carried separately from edge magnitudes and represents the
presynaptic transmitter proxy used by the Paper XVI carrier preparation.

## Run the Fixture

From the runtime repository root:

```bash
python -m applications.malecns_profile_census.prepare_input \
  --fixture examples/malecns_profile_census/tiny-fixture.json \
  --output runs/malecns-profile-census/tiny.input.bin
python tools/build_rust_plugins.py --engineering
python -m applications.malecns_profile_census.replay \
  --input runs/malecns-profile-census/tiny.input.bin
python -m unittest tests.cross_language.test_malecns_profile_census -v
```

The fixture checks exact rescaling invariance, positive and negative source
signs, empty profile fibers, coordinate-specific separation, and deterministic
replay. It is only a protocol and implementation-parity fixture; it is not a
performance benchmark.

## Prepare From the Paper XVI Carrier

Once the paper-owned carrier files are available locally, the same packet
format can be prepared without modifying Paper XVI's frozen files:

```bash
python -m applications.malecns_profile_census.prepare_input \
  --edges-npz <carrier_v0_edges.npz> \
  --nodes-parquet <carrier_v0_nodes.parquet> \
  --field somaSide \
  --output runs/malecns-profile-census/somaside.input.bin
python -m applications.malecns_profile_census.replay \
  --input runs/malecns-profile-census/somaside.input.bin \
  > runs/malecns-profile-census/somaside.replay.json
```

The packet header binds the exact carrier file names, sizes, and SHA-256
digests. Preparation accepts only the Paper XVI release-anchored carrier
identities (`c94e885c...d6966d` for edges and `87aa4628...70515e` for nodes).
It also checks the registered 211,577-node, 25,214,058 known-edge, and
163,439 eligible-source counts before writing the packet.
The packet digest alone does not establish source completeness. The completed
[full-carrier baseline](FULL_CARRIER_READOUT.md) uses externally located carrier
files with those exact release identities; it does not require reprocessing the
1.05 GB upstream weight table. "Full" means all eligible known-sign source rows,
not every node or every unknown-sign edge in the original dataset.

## Controlled Full-Carrier Baseline

The fixed [measurement plan](BENCHMARK_PLAN.md) separates common input
preparation from execution. Both serial implementations run as fresh processes
on the same filesystem-cache-warmed packet, with one excluded warmup each and
five alternating measured pairs. Streaming decode, validation and aggregation
are deliberately one combined phase. Optional `--metrics` emits diagnostics
to stderr while leaving the semantic JSON on stdout unchanged.

Install the preparation/measurement dependencies (`numpy`, `pandas`, `scipy`,
`pyarrow`, `psutil`) in the selected Python environment; exact versions for the
retained run are recorded in its receipt. From this local runtime checkout:

```bash
python -B -m unittest tests.cross_language.test_malecns_profile_census tests.cross_language.test_malecns_profile_benchmark -v
python -B -m applications.malecns_profile_census.benchmark \
  --edges-npz <carrier_v0_edges.npz> \
  --nodes-parquet <carrier_v0_nodes.parquet> \
  --output-dir runs/malecns-profile-census/NEW-BASELINE
```

The output directory must not exist. The command builds the locked release
binary before timing, verifies the complete source identities, prepares the
packet, checks all outputs, and binds sources/input before and after the run.
It terminates and reaps failed or limited children. The compact retained
[receipt](results/full-carrier-somaside.v1/benchmark.v1.json) and
[semantic result](results/full-carrier-somaside.v1/semantic-result.json)
come from the completed local run. Large packets remain under ignored `runs/`.
This is not a clean-checkout/public-release claim; carrier inputs must be
obtained separately by their pinned identities. The source provenance is
retained with [Paper XVI](https://github.com/dooven-prime/rime-lite/tree/paper16-v1.0/experiments/paper16).

## Prepared Input Cache v1

The independent [cache contract](PREPARED_INPUT_CACHE_V1.md) binds source
content, sector/sign policies, format and preparer version/closure into the
cache key. It does not accept a filename's existence as validity. The Rust
kernel validates the whole packet, uses a per-key OS lock, publishes only
complete staging directories, and can execute the census under that lock.
Default behavior rejects invalid entries. Explicit `rebuild` preserves the
bad entry in quarantine before preparing a replacement.

From this local checkout, with the census binary already built:

```bash
cargo build --release --locked --manifest-path plugins/rust/prepared-input-cache/Cargo.toml
python -B -m applications.malecns_profile_census.prepared_cache \
  --cache-root runs/malecns-profile-census/prepared-cache \
  --edges-npz <carrier_v0_edges.npz> \
  --nodes-parquet <carrier_v0_nodes.parquet> --execute
```

The same command validates and reuses a completed entry on the next call.
Add `--invalid-policy rebuild` only when rebuilding an invalid entry is
intended. JSON distinguishes `CACHE_MISS_PREPARED`, `CACHE_HIT_VALIDATED`,
`CACHE_INVALID_REJECTED` and `CACHE_INVALID_REBUILT`; failures exit nonzero.
`--fixture examples/malecns_profile_census/tiny-fixture.json` can replace the
two carrier arguments for a separate fixture-scoped cache.

The [cache measurement protocol](CACHE_BENCHMARK_PLAN_V1.md) separates first
preparation, identity construction, validated hits, execution and explicit
rebuilding. The completed [cache readout](CACHE_READOUT_V1.md) and its
[separate receipt](results/prepared-cache.v1/cache-benchmark.v1.json) preserve
the earlier serial baseline unchanged. To repeat it, use a new output directory:

```bash
python -B -m applications.malecns_profile_census.cache_benchmark \
  --edges-npz <carrier_v0_edges.npz> \
  --nodes-parquet <carrier_v0_nodes.parquet> \
  --output-dir runs/malecns-profile-census/NEW-CACHE-BASELINE
python -B -m unittest tests.cross_language.test_prepared_input_cache -v
```

The cache is a trusted-local-filesystem protocol with process-interruption
tests, not a sandbox, remote cache, power-loss guarantee or exactly-once
executor. Abandoned staging is ignored; automatic garbage collection and
general descendant-process cancellation are not supplied. A caller must not
assume that a validated path remains valid after returning without the locked
consumer operation. Existing serial baseline evidence is not overwritten.

## Cache Hit Cost Decomposition

The separate [cost plan](CACHE_COST_PLAN_V1.md) and completed
[readout](CACHE_COST_READOUT_V1.md) distinguish identity derivation, content
verification, packet validation, execution and process boundaries. Reusing a
fixed admitted request retains every Rust v1 check; neither the measurement
worker nor an old receipt grants permission to skip source/packet validation.
The bounded Rust worker showed no stable complete-hit advantage in this run
and remains an experimental probe, not a production service.

```bash
python -B -m applications.malecns_profile_census.cache_cost_decomposition \
  --edges-npz <carrier_v0_edges.npz> --nodes-parquet <carrier_v0_nodes.parquet> \
  --output-dir runs/malecns-profile-census/NEW-COST-DECOMPOSITION
python -B -m unittest tests.cross_language.test_cache_cost_decomposition -v
```

The new output directory must not exist. The controller builds the separate
probe, checks both historical source/binary closures, records first use,
rotating hit modes, direct consecutive batches and fresh-process session
totals, and compares every complete output to the original serial result.
The [compact receipt](results/cache-cost.v1/cost-decomposition.v1.json) is a
selected local measurement record, not a public-release or independent
validation claim. Structural credentials and immutable input snapshots remain
unimplemented, with their required trust and consumption conditions stated
in the readout.

## Hash/Parse Fusion Experiment

The [fusion plan](FUSED_VALIDATION_PLAN_V1.md) and
[completed readout](FUSED_VALIDATION_READOUT_V1.md) compare the two-pass
validator with hashing below the same buffered parser. Both modes retain v1
source/preparer/consumer checks and post-consumption packet validation. The
separate experiment does not overwrite v1 or introduce validation credentials.

```bash
python -B -m applications.malecns_profile_census.fused_validation_benchmark \
  --edges-npz <carrier_v0_edges.npz> --nodes-parquet <carrier_v0_nodes.parquet> \
  --output-dir runs/malecns-profile-census/NEW-FUSION-COMPARISON
python -B -m unittest tests.cross_language.test_fused_packet_validation -v
```

Use a new output directory and the separately installed preparation/measurement
dependencies listed above. The local controller builds its own locked Rust
binary, checks all three earlier evidence closures and compares full census
outputs. Its [receipt](results/packet-fusion.v1/fusion-benchmark.v1.json) reports
validation read counts, CPU, wall and memory separately. CPU measurement in
this prototype currently requires Windows. This remains local engineering
evidence, not a clean-checkout release or a new SOF capability.

## Boundary

The application is an offline replay workload for the runtime's future data
plane. It is not a SOF canonical carrier, a Solana workload, a biological
validation, or an independent reproduction of Paper XVI. The profile
characterization is the mathematical basis for grouping; the program verifies
only the finite supplied packet. Timing values in the older `replay.py` receipt
remain diagnostic, not controlled benchmarks. The separately planned baseline
supports only its recorded serial-streaming performance comparison. It does
not establish cold-cache I/O, resident kernel speed, parallel or distributed
scaling, exact rational dynamics, Solana throughput, exactly-once processing or
production reliability. No speedup is generalized beyond that workload and
environment.
