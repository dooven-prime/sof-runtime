# Parallel Fiber Checker v0: Local Readout

## Result

The [v0 contract](CONTRACT.md) has a working local implementation: Python
global saturation and typed compilation, fresh Rust shard processes, global
fiber reduction, and saved-closure checking. Workers return signature variants
and state membership, never PASS. This is an application acceptance prototype,
not a Paper XL revision, SOF admission, independent certificate, distributed
enumerator or performance result.

The [compact control record](results/controls.v0.json) records nine existing
typed Q2 controls at each of 2, 3 and 4 shards:

| Control | Global result at each shard count |
| --- | --- |
| `gamma_n2`, `gamma_n3`, `gamma_n4` | `PASS_EXACT` |
| `packet_only`, `count_state` | `PASS_EXACT` |
| `forget_ports`, `forget_origin` | `FAIL_READ` |
| `forget_partition` | `FAIL_GUARD` |
| `parity_only` | `FAIL_SUCCESSOR` |

All 27 decisions and failure clauses agree with the serial checker: 15 passes,
6 read failures, 3 guard failures and 3 successor failures. All 12 rejections
pass the existing streaming history replay. All 27 saved closures pass
`verify_run`, including exact regenerated domains, file digests and decisions.

The three existing environments have respectively 6/39/292 generated log
states and 4/18/72 registered causal summaries. These are different state
spaces, not alternative counts of forest invocations. Saturation has no word
length cutoff. V0 is deliberately limited to 2--4 carrier positions.

## Cross-Shard Failure

In `forget_ports` with four shards, the four causal summaries are assigned one
per shard. Every worker reports COMPLETE with zero local conflicts. The global
reducer nevertheless returns `FAIL_READ`, on `origin_port0`, with actual
histories `d` and `pd`. The selected block and candidate q agree; the parent
block bound to the first kernel port does not. The rejection independently
replays through the existing streaming verifier.

This directly tests why local absence of conflicts cannot authorize global
PASS. Worker COMPLETE means that its assigned computation finished; it is
neither a mathematical sufficiency result nor a coverage proof by itself.

## Focused Verification

The new cross-language suite has 13 passing tests in both ordinary Python and
`-O` mode. It covers all current compiled expression constructors, primitives
and literal sorts, exact large Nat arithmetic, Option-none, duplicate action
labels, atom renaming and reversed port order. These are bounded conformance
controls, not a proof of interpreter equivalence for all expressions.

Hostile paths cover missing/duplicate/foreign coverage, altered binding,
forged signatures, corrupted histories, failed rejection replay, a changed
implementation closure, pre-existing output directories and modified saved
decisions. Real process controls include launch failure, invalid task exit,
timeout and killing workers. These paths return UNRESOLVED, not PASS. Resource
stops and empty registration also cannot yield PASS.

The unchanged Python Q2 suite passes all 24 tests, including its frozen-source
differential test with an explicit RIME source root. The new Rust crate passes
two unit tests and `cargo fmt --check`. No full repository test result is
claimed by these focused runs.

## Retention and Trust Boundary

Full local closures are under `runs/q2-parallel/fiber-v0-controls/`, one
directory per control/shard count. They retain request, plan, all shard tasks
and outputs, decision and receipt. `runs/` remains ignored. Only the compact
matrix is selected here; it binds each receipt hash and the code/binary
closure, but is not itself a self-contained public replay package.

Use the [README commands](README.md#run-locally) to generate a new matrix in a
new directory. `--verify-run` checks saved files and reruns enumeration,
reference evaluation, reduction and rejection replay; it does not rerun the
Rust processes or authenticate the receipt. Binary, Python executable and
source identities are local bindings, not external execution attestations.

Most importantly, the reducer still regenerates the entire domain and
recomputes every worker signature in Python. This prevents omitted or forged
worker summaries from supporting a pass at this acceptance stage, but
duplicates work. Timings in receipts are diagnostic, not a speedup benchmark.
Removing that reference gate, scaling enumeration, using remote workers and
promoting a public evidence snapshot each require separate acceptance work.

The sparse MaleCNS kernel remains a separate next engineering gate. Task
binding and lifecycle patterns may be reused; q-fiber consistency cannot stand
in for another workload's aggregation, ordering or recovery law.
