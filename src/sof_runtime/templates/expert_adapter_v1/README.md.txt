# __DOMAIN_SLUG__ adapter scaffold

Status: scaffold, not runnable.

Fill in `adapter.py`, replace the placeholder declaration and source fixture,
then add positive and hostile tests. Run the case only after every adapter
method returns a contract-valid JSON object.

The adapter owns domain semantics and declared boundaries. `sof-runtime`
owns the Manifest, Typed SOF IR, CompilerOutput, SOFRS report, and validation
receipts. The adapter must not manufacture those runtime-owned artifacts.

## Known non-claims

- The scaffold does not establish a carrier, observable, or domain adequacy.
- Missing implementation is not an unavailable result or a zero finding.
- A passing runtime receipt would establish protocol and artifact closure only.
