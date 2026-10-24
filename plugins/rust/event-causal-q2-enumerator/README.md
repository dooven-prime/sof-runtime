# Q2 Rust Feasibility Prototype

This Rust executable is a technical-feasibility prototype for enumerating one
fixed control family: cyclic `p`, defect map
`d(1)=0`, singleton seed, and selected carrier `{0,1}`. It is deliberately
not a `sof-runtime` external plugin: `ECC_SYN_V1` is a local research input,
not a `sof.run-request.v1` contract, and no SOF artifact, certificate, or
admission is emitted.

The kernel saturates the exact `(partition, chronological fusion log)` state
space and deduplicates full Gamma data: final partition, selected carrier,
formal origin parents, and full later carrier fusions. It uses `u128` partition
bit matrices and exact hash keys; it does not use probabilistic hashes as
semantic identities.

## Build and run

From the runtime repository root:

```bash
cargo build --release --locked --manifest-path plugins/rust/event-causal-q2-enumerator/Cargo.toml
plugins/rust/event-causal-q2-enumerator/target/release/event-causal-q2-enumerator 6
```

The second argument optionally sets the maximum number of log states (default
1,000,000). Reaching it before closure exits as a failure, not an exact result.
The current cross-language fixtures assert exact counts for n=3..6 against the
Python producer; larger runs are engineering experiments until similarly
cross-checked. This prototype is not wired as a selectable `q2_cli.py`
backend, so the existing Python engine and independent rejection replay remain
the application path of record.
