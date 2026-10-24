# Signed Sparse Action: Bounded Benchmark v0

Freeze this plan before measurements. Preserve all earlier profile, cache,
fusion and Q2 evidence. Run one application-owned full-carrier case, not a new
paper release, installed plugin API or hardware-independent speed claim.

1. Verify pinned node/edge artifacts and build source integer CSR. Record
   decoding, hashing, source construction and source re-verification. Build
   the target-row integer packet and record conversion, validation and writing.
2. Verify the packet independently in Python and each Rust process. Build
   SciPy binary64 Y from source rows, compare its transpose CSC view with a
   physical CSR copy. Report numeric coefficient construction and five
   transpose-to-CSR conversion samples separately.
3. Fix two complete input vectors: `dense_nonnegative_v0` with coordinate
   `(37*i mod 1009)/1009`, and a one-hot vector at the largest-mass positive
   source (first index on ties). Both belong to [0,1]^n. Bind their complete
   canonical values. Do not select vectors based on a performance outcome.
4. For each vector, separately measure SpMV and the full clipped/leaky update.
   Use four iterations per resident sample, one excluded warmup and five
   samples. Alternate SciPy CSC/CSR order across samples. Run fresh Rust
   processes at 1/2/4 threads, reversing thread order between workloads.
   Each sample resets its initial vector. SpMV uses constant input; updates
   are a four-step recurrence. Compare all output coordinates to SciPy and
   serial Rust; identical row order requires bitwise Rust thread parity.
5. Exact controls: fixture rational trajectories with cancellation, negative
   drive, both clipping bounds, empty rows and tiny rational differences;
   full-carrier one-hot SpMV and one full update at 1 and 4 threads, checked
   against independent Python Fraction source-row accumulation. Do not
   describe this as all-source/full-orbit exact reproduction of XVII.
6. Record observed RSS/OS peak, sampled CPU lower bound and process wall for
   each Rust invocation. Kernel samples exclude decode/validation, coefficient
   conversion, pool construction and serialization. These costs remain in
   the process total. Record Python controller RSS/CPU as a separate scope;
   do not compare those peaks as if identical process boundaries.
7. Report per-action resident medians, complete invocation measurements,
   layout-only amortization and cross-language preparation-inclusive estimates.
   Layout break-even uses measured float CSR-copy cost and positive CSC/CSR
   savings, never an assumed win. Show totals at 1/4/16/64/256 actions. This is
   a linear estimate, not timed long trajectories or a sharp complexity bound.

Set native BLAS/OpenMP thread environment to one; Rayon uses only its explicit
pool. Cargo builds are untimed, locked; record Python, NumPy, SciPy, CPU,
affinity, memory and Rust identities. This is a shared machine, not an exclusive
reservation. Matrix/vector bytes are memory-resident during samples; no cold
page-cache or production throughput claim. Child limits: 300 seconds, observed
8 GiB RSS; polling is cooperative and not a kernel-enforced sandbox. The first
preparation is measured once; any interrupted run is incomplete, not a PASS.
Check carrier/packet/code hashes after all runs. Keep full outputs under runs;
select only a compact, explicitly non-public-complete local receipt.
