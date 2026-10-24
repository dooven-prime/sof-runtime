# Fixed Capture Acceptance v0

1. Do not modify frozen MaleCNS or Q2 implementations/receipts. Use a new
   application and crate, no service/API registration or generic plugin ABI.
2. Preserve the failed recent devnet capture (unsupported v1) as an incomplete
   attempt. Use the explicit historical finalized devnet range
   378967388--378967390 as the real legacy/v0 sample. Do not omit or filter
   transactions to obtain version coverage. Record current observed server
   version separately from historical block-producing software, which is not
   determined by getVersion. The source is the public devnet RPC endpoint.
3. Independently project the complete captured bytes in Python and Rust. Compare
   canonical JSONL byte-for-byte, slot coverage, source transaction counts,
   complete ordered records and output digest. Confirm repeated execution is
   a no-op on the same state, and fresh execution in a second directory has
   the same projection. No word/event sampling or count-only acceptance.
4. For each of six named commit boundaries, start a real child, wait for its
   exact boundary marker, kill it from Python, reap it, then restart on the
   same state directory. Compare the complete final projection and checkpoint
   to the clean run. Test orphan adoption, partial writes and complete-prefix
   aggregate rebuilding; killed attempts are not successful runs themselves.
5. Run separately labelled synthetic controls for unlisted slots, v0 loaded
   address resolution, failed transactions and repeated payloads. Refuse
   unsupported versions, missing metadata, RPC errors, malformed addresses,
   index/config/root/chain mismatches, altered bytes/duplicate JSON keys,
   unsafe paths, corrupt state, capture identity changes and concurrent writers.
6. Only after the correctness gates, run five fresh invocations, each followed
   by an idempotent repeat. Record full invocation wall time, sampled CPU,
   RSS/OS peak, decode/validation/projection, commit and restart cost. The sample
   is tiny and previously read: no cold-cache, p99, production throughput,
   power-loss, malicious-storage or external exactly-once claim. Throughput is
   diagnostic transactions per complete local invocation, not a network SLO.
7. Bind source capture inventory, request/response hashes, executable and code,
   compiler/environment, reference output and all observed attempts into a
   local receipt. Full capture/output/state/logs stay in ignored runs. Retain
   a selected compact receipt with an explicit non-public-complete boundary;
   source bytes/hashes are not authenticated consensus certificates.
