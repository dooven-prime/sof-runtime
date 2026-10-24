# Shared A0 Extraction Review v0

Local engineering gate for one internal library extraction, not a runtime
service, common process controller or receipt API. See the
[scope review](../../docs/internal/SHARED_A0_EXTRACTION_REVIEW_V0.md) and
[SOF guard](../../docs/internal/SOF_COMPATIBILITY_GUARD_V0.md).

The harness preserves the prior candidate source/executable, checks a protected
SOF byte/test closure before and after, reuses both unchanged application
acceptance matrices, and compares new results with the prior accepted controls.
Reference Python inspection is intentionally independent from Rust; only the
Rust mechanism is single-sourced.

```powershell
python -B -m applications.shared_a0_extraction_review.review capture runs/shared-a0-extraction-v0/NEW-BEFORE
python -B -m applications.shared_a0_extraction_review.review accept runs/shared-a0-extraction-v0/NEW-AFTER --before runs/shared-a0-extraction-v0/NEW-BEFORE
python -B -m applications.shared_a0_extraction_review.review verify runs/shared-a0-extraction-v0/NEW-AFTER
```

Capture must run against the old accepted candidate **before** changing it.
After extraction, do not label a new current-source capture as the old
implementation. The `capture-snapshot` mode only retries an environmental SOF
baseline failure using an already saved old source/executable snapshot; every
byte is checked against the old receipts, and the failed baseline is retained.

The selected run and any environmental retry are described in
[READOUT_V0.md](READOUT_V0.md). It requires ignored local original inputs and
is not a self-contained public replay package. Saved verification checks bytes,
bindings and Python decisions but does not reexecute Rust, the compatibility
test suite or historical kill events. A local PASS is not external attestation.
