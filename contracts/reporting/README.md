# Reporting Contracts

`v2.0/` is the immutable runtime snapshot of the published SOFRS v2 report,
Assembly Profile, and validation-receipt contracts. Its upstream paths,
digests, and release-content commit are recorded in `../upstream.lock.json`.

Runtime conformance establishes assembly and validation relative to these
published bytes. It does not establish adapter adequacy or scientific validity.

`v2.1/` contains exactly the published SOFRS v2.1 report and receipt schemas.
New Level 1B runs generate v2.1 by default. The Assembly Profile remains v2.0;
it is shared by design rather than copied under a false v2.1 identity. The
runtime preserves the frozen v2.0 assembler/validator for historical receipts
and provides an explicit v2.0-to-v2.1 migrator that creates a new receipt.
