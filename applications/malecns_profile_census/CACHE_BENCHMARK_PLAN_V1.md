# Prepared-Input Cache Baseline v1

Fixed before execution. Scope: the unchanged complete `somaSide` carrier,
the existing serial Rust census, and Prepared Input Cache v1 on one trusted
local filesystem. Preserve every byte of the earlier serial baseline.

Build the new cache crate before timing. Each attempt runs the public local
Python cache CLI in a fresh process with the same one-thread environment as
the earlier baseline. The controller measures complete process wall time;
the CLI separately reports identity/request construction, Rust cache process
and workflow times. The Rust cache reports source checks, lock wait, cache
validation, preparation when needed, consumer execution and final checks.
No field stands for a pure arithmetic kernel or a free cache lookup.

Use a new empty output/cache directory and this fixed sequence:

1. One first miss, preparing and executing the complete packet.
2. Five validated cache hits, each executing the same census.
3. Change one byte only in this run's cached packet, not in its sources or
   any old baseline. Default policy must reject it without a consumer run.
4. One explicit `rebuild`: quarantine that entry, prepare, validate and execute.
5. One post-rebuild validated hit and execution.

All eight successful outputs must exactly equal the retained original
canonical semantic result, including its exact profile-class digest. Every
prepared packet must have the original packet's length and SHA-256. Status
order, no preparation on hits, and no execution on rejection are acceptance
conditions. Source/key/code bindings must stay unchanged throughout.

Report the miss and rebuild as individual observations, not statistical
estimates. Summarize the five ordinary hits with minimum/median/maximum;
retain every observation. Timings include content verification and cannot
be compared with the old unvalidated census time as equivalent obligations.
No OS cache eviction or exclusive CPU reservation is performed. This is not
a cold-cache, persistent-kernel, parallel, distributed or Solana benchmark.

The separate fixture suite supplies real-process interruption, concurrent
same-key building, bounded lock wait, source changes, malformed metadata and
consumer identity tests. The full carrier run does not corrupt a published
source or repeat those destructive tests on it. Child preparation/execution
timeouts come from the cache request; the outer controller has a 1,200-second
attempt deadline. These are cooperative process controls, not a sandbox or
power-loss guarantee. No success depends on a preset speedup threshold.
