# Packet Validation Fusion

Separate local experiment, not a replacement for the frozen cache-v1 binary.
The application owns the [plan](../../../applications/malecns_profile_census/FUSED_VALIDATION_PLAN_V1.md)
and [readout](../../../applications/malecns_profile_census/FUSED_VALIDATION_READOUT_V1.md).
There is no worker or reusable validation credential.

```bash
cargo build --release --locked --manifest-path plugins/rust/packet-validation-fusion/Cargo.toml
cargo test --locked --manifest-path plugins/rust/packet-validation-fusion/Cargo.toml
python -B -m unittest tests.cross_language.test_fused_packet_validation -v
```

The local binary accepts:

```text
packet-validation-fusion reference|fused execute|validate REQUEST.json
```

`execute` runs the cache protocol including its consumer and final checks.
`validate` only measures entry validation and grants no future path-consumption
authority. Both consume the existing v1 request format. The experiment envelope
contains the nested cache result, validation-call timings, CPU time and read
counters. Failures exit nonzero. CPU counters currently use Windows
`GetProcessTimes`; other platforms return unavailable, not zero, and the
measurement controller rejects an unavailable CPU field.

## Source and Equivalence Boundary

`build.rs` SHA-pins the original `prepared-input-cache/src/main.rs`, parses it
with `syn`, preserves its execution code and derives the parser directly from
the original validation statements. Shape checks guard the split between
regular-file/hash/open setup, the parser predicates, and final packet assembly.
The generated Rust is confined to Cargo's build directory. The original file
is not written. The build fails if its digest or expected shape changes.

The control is the original two-pass validator, with read instrumentation.
The candidate hashes returned file bytes below an otherwise unchanged default
`BufReader`, then assembles the packet only after the shared parser's EOF and
count checks succeed. No buffer-size optimization is bundled into fusion.

Counters wrap the two original read-open sites (hashing and packet parsing)
and the candidate's read-open site. They count opens, `Read` invocations,
positive reads and bytes returned. Manifest/request reads and census-child
I/O are not instrumented; these counters are not physical disk counters.
Instrumentation is present in both modes.

Accepted packet records agree for stable inputs. Invalid data may be rejected
earlier by the fused reader; no claim of identical failure latency or error
precedence under I/O races is made. The original pre/post source checks,
manifest bindings, consumer checks and final packet comparison remain active.
The trusted-local-filesystem and immutable-through-invocation assumptions are
unchanged. This is neither a snapshot mechanism nor malicious-writer defense.
