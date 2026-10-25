# Cache Hit Cost Decomposition v1

## Question and Frozen Controls

Which work can be reused without reducing Prepared Input Cache v1's checks?
This is a separate, local engineering experiment. Do not edit the original
serial baseline, cache implementation, contracts, or their retained receipts.
Bind both historical closures and this probe's sources/binaries before and
after measurement. The workload and complete semantic golden output remain
the full `somaSide` carrier, not a smaller fixture.

## Reuse Boundary

The only implemented reuse is an already constructed, exact request and a
bounded sequential Rust process. A reused request declares the same desired
source bytes, policies, preparer and consumer, rather than asking the caller
to discover a new current environment. The controller rechecks the declared
Python/dependency versions on every reused call. Source bytes, preparer files,
interpreter, packet and consumer executable are still checked by v1 on every
execution. Environment and filesystem trust assumptions remain v1's; version
strings are not proofs of installed package contents.

The probe includes the unchanged v1 Rust source as a module and calls its
`execute` function. It does not maintain packet/source validation credentials,
skip checks, change locking, or keep the census kernel resident. Every census
still runs in a fresh child. The probe is not an installed runtime API.

The JSONL worker admits one request at a time, at most 64 per process, at most
1 MB per request. It acknowledges startup and echoes sequential IDs. EOF ends
the session; malformed framing/schema/IDs end it unsuccessfully. A normal v1
rejection is returned for that call and does not validate a later call. There
is no background service, automatic retry, shared mutable request registry or
cross-process credential. The Python controller times out, kills and reaps its
worker; v1's existing limitation on descendant cancellation remains. Restart
retains only the filesystem cache and revalidates it. Source/policy/format or
preparer changes require a newly admitted identity, never a metadata shortcut.

## Fixed Sequence

1. Build outside timing. Snapshot old/new closures. Create a new output/cache
   directory; never mutate an old cache or packet.
2. Measure first fresh-Python CLI miss, including identity, preparation,
   verification and census. This is process-cold, not filesystem-cache-cold.
3. Construct one fixed request. Measure worker startup to READY and its first
   complete hit separately. Exclude one fresh-process warmup hit from summaries.
4. Five rounds, rotating order: original fresh Python CLI; fixed request with
   fresh v1 Rust process; fixed request with sequential Rust worker. Check
   complete semantic outputs after each success. Measure each round's whole
   wall time, not a sum of internal timers.
5. Five consecutive hits in each fixed-request mode, timing the complete batch
   independently. Request construction and worker startup are reported outside
   batch timing; per-call environment checks and IPC are inside it.
   Also measure a separate fresh Python process per mode that constructs its
   identity once, consumes five times and closes its worker (when applicable).
   Record that whole process and session wall directly, not as a component sum.
6. Three fresh-process instrumented identity constructions: wrap the original
   factory's hashes, dependency-version calls, PyArrow import and table read.
   No replacement identity logic. Record unassigned conversion/normalization
   and other time as residual; do not label it pure arithmetic.
7. Five isolated Rust probes: v1 source/preparer verification; packet SHA only;
   complete v1 entry validation. These are separate repeated reads, not an
   additive decomposition of a particular execution. Do not infer exact parse
   time by subtracting medians. Five fresh and five worker no-op pings measure
   process/transport overhead only, not the validation workflow.
8. Snapshot closures again. Retain compact receipt and readout; packets remain
   under ignored `runs/`. Tests/fault injections run outside measurements.

## Reporting and Decision Rules

Record individual samples, min/median/max, machine, versions, source identity,
complete output digest, protocol statuses, startup, miss, first hit, steady
calls, consecutive batches, and end-to-end process/round walls. Timers are
nested or overlapping; do not add their medians. No disk-cache eviction, CPU
reservation, speedup extrapolation, parallel claim or percentile SLO.

Repeated identity metadata derivation may be reused for a fixed admitted
request while source content remains revalidated. Full source/packet hashes
and structural checks remain per-call in this experiment. A future structural
credential must bind validator version, exact packet digest/length, canonical
header/policy and successful structural result, and must re-establish those
exact bytes at consumption. Merely storing those fields is not independent
attestation. Skipping even the byte recheck requires a separately enforced
immutable/owned snapshot capability, which is not implemented here.

Do not promote a worker based only on no-op latency. Compare complete hit and
batch times under identical checks; unchanged or noisy results are valid
negative outcomes. This study does not claim a production worker, cached
scientific adequacy, power-loss safety, malicious-writer protection or Solana
performance.
