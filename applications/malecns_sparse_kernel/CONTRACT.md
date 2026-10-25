# MaleCNS Sparse Action v0

## Fixed Mathematics

Use the published 211,577-node basis, 25,214,058 known-sign edges and the
existing presynaptic transmitter proxy. Unknown-sign rows are zero, not
positive. For positive integer edge weight w, source sign s in {-1,1} and
outgoing absolute mass m, Y[source,target] = s*w/m. Zero-mass rows are zero.
Propagation is Y-transpose times x. The full update is
`4*x/5 + clip(Y-transpose*x,0,1)/5`, with no input or noise. This inherits the
formula, not the published finite-orbit evidence or its biological authority.

Numerical mode uses finite IEEE binary64 coefficients, ascending source order
inside each target row, ordinary multiplication and addition, no explicit FMA
or fast-math. Rayon partitions output rows; the order of each row's sum is
unchanged. Compare complete output against SciPy, reporting maximum absolute
and scaled error, L1/L2 errors and clipping-fate differences. Acceptance is
`abs(error) <= 1e-12 + 1e-12*abs(reference)` at every coordinate. A numerical
pass is not rational equality, especially at clipping boundaries.

Exact mode uses arbitrary-precision reduced rationals in Rust and Python
Fraction. Both the sum and comparisons to 0 and 1 are exact. Numeric input is
never silently substituted for a rational pair. Exact full-carrier controls
are bounded sparse-input workloads, not a replay of every XVII orbit. Task,
iteration and rational-size limits fail closed rather than change arithmetic.

## Target-Row Packet

New format, not the earlier profile-census packet: magic `MSPMV001`, u32-LE
JSON-header length, UTF-8 header, followed by five arrays:
`indptr:u64[n+1], source:u32[nnz], weight:u32[nnz], sign:i8[n], mass:u64[n]`.
The header binds schema, n, nnz and the exact source artifact hashes/policy.
Source indices within each target row are strictly increasing. Weights are
positive; every nonzero source has sign +/-1 and mass equal to its complete
outgoing weight sum; sources without edges have mass zero. Reject truncation,
trailing data, invalid indices, unordered/duplicate entries and inconsistent
mass/sign data. Each consumer verifies the supplied whole-packet SHA-256.

The preparer verifies pinned source hashes before and after reading, removes
unknown-sign edges, builds source CSR, and converts its transpose to target
CSR. It records source decoding, source-CSR construction, transpose-copy
conversion, validation, serialization and whole preparation separately.
No assumption of immutable storage or reusable validation credentials is made.

## Execution and Cost

A request selects arithmetic, `spmv` or `update`, threads, iterations per
sample, warmups, repeats and an explicit vector. SpMV repeats the same input;
update follows the actual recurrence, resetting to the declared input before
each sample. Results retain all coordinates. Kernel samples exclude packet
reading/hash/validation, coefficient conversion, vector decode and output
serialization; those costs remain separately visible. Full process wall/CPU
and sampled/OS peak RSS are recorded by the coordinator. Timings are nested;
do not add them as if disjoint. Rayon pool creation is outside kernel samples
and inside full-process cost. No resident worker or remote execution.

Measure source-transpose CSC and target-CSR SciPy actions on the same resident
vector. Layout break-even is ceil(transpose-copy cost / positive per-action
saving); report unavailable if the saving is nonpositive. Also report the
measured finite iteration totals, not only an extrapolated threshold. A
cross-language saving includes implementation differences and is not a pure
layout effect. Fresh-process and resident-kernel results remain distinct.

## Evidence Boundary

Fixtures check arithmetic and hostile protocol paths. Full-carrier runs bind
carrier, vectors, packet, code, binary, dependencies, outputs and environment.
They are local engineering controls, not new Paper XVI/XVII evidence, exact
quotient claims, production scaling, Solana acceptance or SOF admission.
No speedup, parallel benefit or amortization threshold is an acceptance premise.
Existing benchmarks, receipts and published source bytes remain unchanged.
