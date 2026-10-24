# MaleCNS Sparse Kernel v0: Local Readout

## Scope and Correctness

The [contract](CONTRACT.md) and [predeclared benchmark plan](BENCHMARK_PLAN.md)
are implemented on the pinned 211,577-node/25,214,058-known-sign-edge carrier.
The new target-row packet is 205,309,744 bytes. Unknown-sign source rows are
zero, and the action uses outgoing absolute-row normalization followed by the
incoming transpose. No published carrier or earlier benchmark was modified.

The [selected local receipt](results/benchmark.v0.json) records 16 full-output
comparisons: 12 numerical workloads (two vectors, two operations, 1/2/4
threads), and four exact one-hot controls (SpMV/update at 1/4 threads). All
pass their declared checks. Rust numerical outputs are bitwise identical
across thread counts. Maximum absolute error versus SciPy is `1.42e-14` for
dense SpMV and `3.33e-16` for the four-step dense update, within the declared
`1e-12 + 1e-12*abs(reference)` bound. All output 0/1-region comparisons agree;
for updates this describes the final output, not an audit of every intermediate
drive's clipping fate.

Exact mode agrees with independent source-row Python Fraction accumulation at
all 211,577 coordinates, for the declared one-hot source 38. These controls
perform one action/update, not all-source XVII orbit replay. The seven focused
tests pass in ordinary and `-O` modes: multistep rational fixtures, signed
cancellation, both clipping limits, tiny rational threshold differences,
empty rows, serial/parallel parity, corrupt packet structure and arithmetic
limits. The crate's exact-clipping unit test and format check pass. Tests and
bounded controls are not a general cross-language equivalence proof.

## Resident Numerical Cost

On the recorded i7-13700H/shared Windows machine, medians in milliseconds per
action are below. Each numerical sample has four actions, one excluded warmup
and five retained samples; update samples follow a four-step recurrence.

| Dense nonnegative input | SciPy source-transpose CSC | SciPy target CSR | Rust 1 thread | Rust 2 threads | Rust 4 threads |
| --- | ---: | ---: | ---: | ---: | ---: |
| `Y^T x` | 34.53 | 27.53 | 34.65 | 18.48 | 13.19 |
| Full clipped/leaky update | 35.51 | 29.42 | 33.63 | 19.00 | 14.23 |

Thus Rust serial is not an automatic improvement over SciPy. This local
four-thread target-row implementation improves resident time, without changing
the row summation order. It is not a production scalability result, a
statistical significance claim or an isolated arithmetic-only measurement:
allocation and the complete update operations remain in the kernel samples.

## Conversion and Amortization

Whole initial target-packet preparation took 4.925 seconds, including pinned
source verification, decode, source CSR, target layout, validation, writing and
packet hashing. Integer transpose CSR conversion alone took 0.416 seconds;
target layout plus array materialization took 0.543 seconds. Float SciPy source
coefficient construction took 0.369 seconds. The five float CSC-to-CSR copies
had a 0.429-second median (range 0.397--0.514 seconds).

| Workload | Layout-only estimated actions to recover float CSR-copy cost | Cross-language Rust-4 estimated actions to recover extra target-packet/setup cost |
| --- | ---: | ---: |
| Dense SpMV | 62 | 129 |
| Dense update | 71 | 128 |
| One-hot SpMV | 65 | 143 |
| One-hot update | 26 | 79 |

These are **linear estimates from observed resident medians**, not measured
long trajectories or universal first-hit thresholds. The receipt includes
1/4/16/64/256-action estimated totals and all sample ranges. The one-hot update
CSC samples are particularly variable (about 36--67 ms/action), so its threshold
must not be treated as precise. A nonpositive measured saving is recorded as
unavailable, including serial Rust for both SpMV inputs.

The cross-language estimate includes target layout/materialization, packet
validation/write/hash, Rust read/hash/validation, numeric coefficient conversion
and pool setup. It does not subtract SciPy's coefficient construction cost, and
is not a pure layout comparison. It assumes reuse of resident representation;
it does not amortize repeated fresh-process launches or promise shorter
end-to-end one-shot calls. The initial shared source-read cost is not hidden:
it is retained separately in the full preparation record.

## Process and Retention Boundaries

For dense SpMV, the whole Rust invocation took 1.483 seconds at one thread and
0.975 seconds at four threads, each including warmup plus five four-action
samples and output serialization. The four-thread invocation separately records
0.314 seconds for packet read/hash/decode/validation, 0.082 seconds for numeric
coefficients and 0.136 seconds for the post-consumption packet hash. These are
nested scopes, not terms to add to the kernel median.

Observed Rust numerical RSS peaks are about 526--530 MB; exact controls about
564 MB. Controller OS peak working set is 1.87 GB and includes preparation and
SciPy representations, not the Rust children. CPU observations, process wall,
RSS and OS peaks are distinct fields. Polling can miss a brief peak; no memory
or CPU superiority claim follows from differing process boundaries.

Full requests, reference/output vectors, packet and 55 bound files remain at
`runs/malecns-spmv/full-carrier-v0/`. The saved-closure verifier passes all 16
output comparisons and file hashes without rerunning kernels. The compact
receipt selected here is not the whole public replay package; it has no
independent validation, SOF admission, biological or Solana authority. Commands
and dependencies are in the [README](README.md).

This establishes a finite local kernel baseline with separate exact and
numerical semantics. It does not by itself justify a shared runtime API, a
resident service, an exact full XVII replay or broader parallel generalization.
