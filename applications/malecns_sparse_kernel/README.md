# MaleCNS Signed Sparse Kernel v0

An application-local Rust/Python prototype of the fixed `Y^T x` action and
`4*x/5 + clip(Y^T x)/5` update. See the [arithmetic and packet contract](CONTRACT.md)
and [bounded benchmark plan](BENCHMARK_PLAN.md). It does not change any published
carrier, earlier benchmark, runtime API or canonical SOF claim.

The first full-carrier [local readout](READOUT_V0.md) and
[compact receipt](results/benchmark.v0.json) are retained separately from the
earlier profile-census evidence.

Incoming target rows avoid shared output writes. Numerical mode uses binary64
and SciPy comparisons; exact mode uses Rust BigRational and independent Python
Fraction source-row accumulation. Exact rational clipping is never replaced
with a floating tolerance. Threaded rows retain their serial accumulation order.

## Local Commands

From this checkout's root, with Python 3.11+, NumPy, SciPy, pandas, PyArrow,
psutil, Cargo/Rust 1.89+ and locked crate dependencies:

```powershell
python -B -m unittest tests.cross_language.test_malecns_spmv -v
cargo test --locked --manifest-path plugins/rust/malecns-spmv/Cargo.toml
python -B -m applications.malecns_sparse_kernel.benchmark `
  --edges PATH/TO/carrier_v0_edges.npz `
  --nodes PATH/TO/carrier_v0_nodes.parquet `
  --output-dir runs/malecns-spmv/NEW-FULL-CARRIER-RUN
python -B -m applications.malecns_sparse_kernel.verify `
  runs/malecns-spmv/NEW-FULL-CARRIER-RUN
```

The output directory must not exist. Carrier mode checks the exact published
file hashes, not any file with the same name. These are tested local-checkout
commands, not a clean-checkout/public release claim. Initial Cargo dependency
acquisition can require network access. Full data is not copied into the app.

The benchmark retains all requests, output vectors, references and a target-row
packet under ignored `runs/`. Its receipt binds that inventory, code, binary,
carrier and complete vectors. Verification rechecks saved hashes/comparisons;
it does not rerun kernels or authenticate execution. A selected compact
receipt alone is not a public self-contained replay package.

## Cost Boundaries

Source preparation, transpose/layout conversion, coefficient preparation,
packet validation, resident SpMV, full update, process wall and observed memory
are separate fields. Kernel samples include output allocation and update work,
but not file decode, coefficient conversion, pool setup or serialization.
Reported CPU observations are sampled lower bounds. Controller and Rust-child
memory scopes are different and are not a like-for-like language comparison.

Layout amortization compares SciPy CSC transpose with target CSR; a separate
cross-language estimate includes additional target packet/setup costs and must
not be attributed purely to layout. Estimate tables are not measured long
trajectories. No parallel speedup or positive break-even is assumed.

Full-carrier exact controls cover one selected one-hot vector, one SpMV and one
update. Multistep rational semantics is checked on small mixed-sign fixtures.
This is not a reproduction of all Paper XVII microscopic orbits, a new
biological result, a Solana workload or a production throughput claim.
