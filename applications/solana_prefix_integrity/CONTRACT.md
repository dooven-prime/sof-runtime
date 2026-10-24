# Prefix Integrity Cost Attribution v1

This is a read-only, Windows-local experiment, not a new replay runtime.
Frozen v0/v1 implementations, selected receipts, projection semantics and
transaction support are unchanged. The probe compiles the frozen v1 source
and reuses its capture parser, strict JSON, confinement, digest and continuity
checks. It never decodes/projects a committed block.

## Measured Domain

Use the previously pinned 64-slot capture and exactly 62 committed slots.
Generate each fresh prefix by running the unchanged v1 binary and actually
killing it at the declared checkpoint-publication boundary. The controller
binds that checkpoint hash as the prior validated anchor. Copying does not
establish validity: the probe still checks every prefix input/segment byte.
Fresh and copied states have identical committed content but distinct file
identities. Creation/mtime/file attributes are observations, never credentials.

Four phases are separately timed: checkpoint/anchor/identity/cursor/chain and
inventory checks; prefix raw-response hashes; segment hash/length/record-count
validation; streamed aggregate construction with per-segment revalidation and
sync. Metadata admission and post-consumption stability checks remain separate.
All captured RPC request/response hashes are checked after consumption, as in
v1. The source manifest, plan, state checkpoint and identity are checked again.
The state is locked and never rewritten. Probe output is a new scratch file,
outside state/capture directories. A failed probe has no accepted output.

The aggregate covers the **committed prefix only**, not the unprocessed two
slots. No suffix computation, new commits or complete-capture recovery cost
is attributed to it. Full Python projection independently checks that prefix
after the timed experiment. This is not a substitute for the v1 recovery suite.

## Measurements and Order

The plan fixes four pairs and two explicit read-warm rounds: 24 probe processes.
Pairs alternate fresh-first/copy-first preparation and initial measurement.
In fresh-first pairs, no state copy is made before the fresh initial probe.
In copy-first pairs, the original has necessarily been read by copying; this
is recorded rather than described as a cold control. Each warm probe is
immediately preceded by a recorded sequential read of the same input/segment
files. Fresh/copied order alternates by pair and round. No page-cache flush,
security-service changes, mtime shortcut or reusable validation credential.

Wall and process user/kernel CPU deltas, Windows process I/O accounting,
stream-returned byte counts, per-file timings and before/after file metadata
are retained. Logical bytes and process I/O counters do not measure physical
disk reads or isolate Defender, filesystem, scheduling and cache mechanisms.
Short phase CPU readings can be quantized; zero is not proof of zero work.
Per-file nested times are diagnostic subsets, not additional costs to add.

## Stop Rule

Execute the frozen plan once. Classify only bounded CPU-vs-non-CPU and file-state
sensitivity; a non-CPU attribution is not an exact storage-device diagnosis.
If at least three pairs show both the planned wall/CPU and initial-copy/warm
ratios, stop fixed-capture acceleration work. If process CPU instead dominates,
record a candidate only, with no tuning in this experiment. Otherwise retain
UNRESOLVED attribution and stop. Neither outcome authorizes new cache trust.
Input progression, source correction and checkpoint invalidation remain
separate possible system-semantics work, not implemented by this experiment.
