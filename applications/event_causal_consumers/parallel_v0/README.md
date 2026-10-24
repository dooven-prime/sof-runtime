# Q2 Parallel Fiber Checker v0

Python global enumeration -> fixed state shards -> Rust signatures -> global
reducer -> source-bound local receipt. Workers return fiber summaries, never
PASS. Only the reducer can give application-local `PASS`, `FAIL`, or
`UNRESOLVED`.

This implements the [v0 contract](CONTRACT.md) on existing 2--4 position Q2
environments, using 2--4 shards. The published typed Q2 code and Paper XL
snapshot are not modified. It is not a distributed enumerator, production
worker service, SOF capability or new public paper evidence.

## Run Locally

Requirements: Python 3.11+, Cargo/Rust 1.89+, and the locked Rust dependencies.
Dependency acquisition may require network access on the first build. Python
uses the standard library. Run from the runtime repository root:

```powershell
python -B -m applications.event_causal_consumers.parallel_v0.coordinator `
  applications/event_causal_consumers/examples/origin_read_failure.json `
  --shards 3 --output-dir runs/q2-parallel/NEW-ORIGIN-CONTROL
python -B -m applications.event_causal_consumers.parallel_v0.coordinator `
  --verify-run runs/q2-parallel/NEW-ORIGIN-CONTROL
python -B -m unittest tests.cross_language.test_q2_parallel_fibers -v
```

The output directory must not exist. A completed mathematical rejection exits
0 just as a completed pass does; inspect the JSON status. Unresolved execution
or verification exits 2. Verification of a valid closure containing an
unresolved decision still exits 2. No incomplete result grants admission.

To replay the nine existing controls at each shard count:

```powershell
python -B -m applications.event_causal_consumers.parallel_v0.run_controls `
  --output-dir runs/q2-parallel/NEW-CONTROL-MATRIX
cargo test --locked --manifest-path plugins/rust/q2-fiber-worker/Cargo.toml
```

These are local-checkout workflows, not clean-checkout/public-release claims.
See the [local readout](READOUT.md) for retained results and boundaries.

## What Is Checked

- The Python enumerator saturates the complete generated log graph, then forms
  the registered causal image. Histories are predecessors, not state keys.
- The plan binds every state, successor, witness history, shard membership,
  environment, selected F, consumer, q, compiled IR and source/binary version.
- Rust independently evaluates the compiled typed IR and computes actual
  causal successors. It retains every distinct signature within each q fiber,
  including one representative and all member IDs for each variant.
- The reducer verifies exact disjoint coverage and all bindings, then merges
  q fibers across shards. Global R/G/T priority is preserved.
- Every FAIL uses two actual histories and passes the existing separate
  streaming rejection replay. That replay does not certify enumeration.
- The receipt binds saved request, plan, tasks, worker results and decision.
  The separate verification entry reruns the reducer from the saved closure.

**V0 deliberately checks every worker signature again with Python and
regenerates the global domain in the reducer.** This protects the acceptance
prototype against forged summaries and incomplete plans, but duplicates work.
The Rust interpreter is not an independent static type checker, and no speedup
or scalable distributed coverage proof is claimed. Removing these reference
gates would require another explicitly reviewed trust/conformance boundary.

## Limits and Reuse

Workers accept one bounded task file, use exact arbitrary-precision Nat
arithmetic, and reject/stop on step, depth, input or value bounds. The parent
times out, kills and reaps workers. Missing/duplicate shards, foreign members,
changed versions, crashes, invalid signatures and failed witness replay are
unresolved, never global passes. Empty registration is not a supplied source.

The reusable part is task binding, lifecycle, error handling and receipt
construction. Mathematical reduction remains workload-specific: q-fiber
consistency here, exact class aggregation for MaleCNS, and separately declared
ordering/fork/checkpoint rules for any future Solana application. This prototype
does not replace the separately planned sparse-kernel work or change any
canonical SOF status, published source or release identity.
