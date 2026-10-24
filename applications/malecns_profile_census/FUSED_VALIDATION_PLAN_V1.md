# Packet Hash/Parse Fusion Experiment v1

## Scope

Change implementation, not cache validity. Compare a two-pass reference
validator with a one-pass hash/parse validator on the same admitted request,
manifest, packet, serial consumer and full `somaSide` carrier. Keep all previous
sources, binaries and receipts unchanged. No worker, validation credential,
trusted storage, new SOF field, sparse kernel or Solana workload is added here.

The separate Rust binary imports a SHA-pinned v1 source through a structured
Rust AST transformation. It renames the original validator for the control,
derives the parser from that exact function's statements and instruments its
two read-open sites. Cache execution, locks, input/preparer/consumer identity
checks, staging and post-consumption comparison remain the v1 code. The
generated AST is a build artifact, not an edited replacement of frozen source.
Build-time shape checks fail closed if the pinned implementation changes.

The reference retains its separate full hash and buffered parse. Fusion puts
a hashing reader below the same default `BufReader`: each returned byte chunk
is hashed once as it enters the parser's buffer. The parser's required EOF
test must succeed before digest/length are returned. Buffer sizing is not
changed. Rejected packets need not be completely hashed and may fail earlier;
acceptance and successful packet records must agree on stable inputs.

## Correctness Gate

1. Read-only/immutable-through-invocation inputs and v1's trusted-local
   filesystem assumptions remain required. This is not adversarial TOCTOU or
   power-loss protection.
2. Both modes share every original structure predicate, canonical-header
   comparison, count, overflow and EOF check. For stable accepted bytes they
   return identical header, counts, size and SHA-256.
3. Differential tests cover valid fixtures; truncation at every offset of the
   small packet; byte corruption; wrong and noncanonical headers; extra bytes;
   invalid order/sign/sector/weight/mass; manifest mismatch; source/preparer
   identity; explicit rebuild; and same-key publication locking.
4. Actual child consumers alter a source or packet before returning, including
   a still-well-formed packet with a changed digest. Both modes must reject
   the call at the retained post-consumption boundary. Default rejection must
   not silently rebuild. No old evidence is mutated for these tests.

## Fixed Measurement

Build and run correctness tests outside timing. Verify old serial, cache-v1
and cost-decomposition closures. Create a new cache and fixed request once;
preparation and identity admission are timed separately, not included in hit
ratios. Warm each mode once for each of two actions. Then run five alternating
pairs for isolated full-entry validation and five for complete cache hit plus
the original serial census. Each attempt is a fresh process. Check complete
semantic output on every successful consumption against the original golden
JSON. No packet/census change, worker, thread sweep or buffer-size sweep.

Record individually and summarize independently:

- process wall time from the Python parent, and internal validation wall time;
- cache-process CPU seconds (all its threads, excludes the census child),
  queried with Windows `GetProcessTimes`; unsupported platforms report this
  unavailable rather than zero;
- sampled root RSS and OS-maintained peak root working set, and sampled peak
  tree RSS separately (not a sum of independently observed peaks);
- instrumented packet opens, actual `Read` calls, positive reads and returned
  byte counts for validation; source/preparer reads remain separately visible;
- one additional logical census read, verified by its complete domain counts,
  but not misreported as instrumented child I/O or physical storage traffic.

Internal timers nest inside process wall and CPU intervals. Do not sum their
medians, subtract unrelated probes or equate logical reads with disk I/O.
Process-tree RSS is sampled and may miss short-lived peaks. The machine is
shared, filesystem cache is warmed, and this is not a cold-I/O or whole-pipeline
CPU benchmark. Unexpected failure or historical closure drift invalidates the
run. Reduced reads alone do not prove a speedup; retain a negative timing
result if that is what occurs.

## Exit Gate

Retain one compact, source-bound receipt and readout with exact parity,
rejection checks and separate resource measurements. Decide whether the
implementation is worth carrying forward, then move to a separately specified
sparse-operator kernel. Credentials remain design-only: skipping consumption
byte verification still needs an enforced immutable snapshot/lifetime and
credential authority, neither supplied by this experiment.
