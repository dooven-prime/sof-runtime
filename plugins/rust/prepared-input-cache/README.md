# Prepared Input Cache v1 Kernel

Application-local Rust cache lifecycle and packet validator. The normative
scope and failure rules are in
[Prepared Input Cache v1](../../../applications/malecns_profile_census/PREPARED_INPUT_CACHE_V1.md).
This executable emits local cache diagnostics, not a SOF certificate or a
production/distributed storage guarantee.

The crate requires Rust 1.89 or later for standard-library OS file locking;
this does not change the older census crate's declared minimum Rust version.

From the runtime repository root:

```text
cargo build --release --locked --manifest-path plugins/rust/prepared-input-cache/Cargo.toml
cargo test --locked --manifest-path plugins/rust/prepared-input-cache/Cargo.toml
python -B -m unittest tests.cross_language.test_prepared_input_cache -v
```

Use the Python request factory/CLI rather than hand-writing absolute paths in
an identity. `prepared-input-cache REQUEST.json` is the low-level process
interface. The factory binds content and policy independently of cache location;
the Rust tool checks the actual sources/preparer and the complete packet.
An optional consumer executes under the per-key lock and has its own bound
executable identity, distinct from the prepared-input key.

Keep old baseline sources and result bytes unchanged. The census stays serial;
this crate adds no thread-level profile aggregation, distribution or Solana
semantics. Interrupted staging may require separate cleanup; it is never
admitted as a published entry.
