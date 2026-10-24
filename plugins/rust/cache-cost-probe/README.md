# Cache Cost Probe

Local measurement harness, not an installed plugin, runtime API or daemon.
Its `execute` action includes the unchanged sibling
`prepared-input-cache/src/main.rs` in a module and calls that implementation.
The locked dependency versions match the reference crate. It does not replace
the existing cache binary or keep source/packet validity across calls.

The application-owned protocol and measurement plan are
[Cache Hit Cost Decomposition v1](../../../applications/malecns_profile_census/CACHE_COST_PLAN_V1.md).
Full-carrier instructions and results are routed from the
[application README](../../../applications/malecns_profile_census/README.md).

```bash
cargo build --release --locked --manifest-path plugins/rust/cache-cost-probe/Cargo.toml
python -B -m unittest tests.cross_language.test_cache_cost_decomposition -v
```

## Bounded JSONL Session

With no arguments, the binary writes READY, then accepts up to 64 sequential
one-line envelopes, each at most 1 MB:

```json
{"schema":"sof-runtime.cache-cost-probe.v1","id":0,"action":"ping","request":null}
```

Actions are `ping`, `execute` and `probe`. The latter two take an entire v1
cache request, not a stored request ID. Every response echoes the envelope ID.
`--once ENVELOPE.json` executes one envelope with ID 0 without READY. EOF
closes a normal session; malformed/oversized framing, invalid schema or
out-of-sequence IDs terminate it with `PROTOCOL_REJECTED` and exit 2. Reaching
64 requests ends the session; callers must explicitly start another process.

An ordinary v1 rejection is a per-call result, not a worker crash; always
inspect the nested result status, not just the process exit code. A failed
call confers no validation authority on the next one. The Python caller has
bounded waits and kills/reaps a timed-out worker. It supplies no general
descendant-process cancellation, sandbox, authentication or network service.

`probe` separately times v1 source/preparer verification, packet hashing and
full entry validation, without consuming the input. These isolated reads are
not a disjoint trace of `execute`; they do not grant authority to consume a
path later. `ping` is only a process/transport control.

No reusable validation credential, persistent kernel, asynchronous work
queue, cross-client concurrency or automatic restart/retry is implemented.
Each `execute` retains v1's locks, complete validation, fresh census child and
post-consumption checks. The full v1 local-filesystem and mutation boundaries
continue to apply. Startup timing is not evidence of production acceptance.
