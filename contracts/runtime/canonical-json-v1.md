# SOF Canonical JSON v1

Identifier: `sof-cjson-v1`.

This profile defines the bytes used for SHA-256 artifact identity and semantic
run identity. It is intentionally narrower than general JSON so independent
languages do not need to reproduce implementation-specific floating-point
formatting.

## Processing Order

1. Parse JSON while rejecting duplicate object keys.
2. Validate the data model against its declared JSON Schema.
3. Verify the canonical-value restrictions below; do not silently repair the
   value.
4. Serialize exactly once using this profile.
5. Compute SHA-256 over the resulting bytes.

Canonicalization occurs after schema validation. The digest excludes a byte
order mark, framing bytes, and any trailing newline.

One failure-evidence exception is permitted: an input rejected by its domain
schema may still be canonicalized and retained with `schema_id: null`. Such an
artifact records the submitted bytes but does not claim schema conformance.

## Data Model

- Values are `null`, Boolean, signed 64-bit integer, NFC string, array, or
  object.
- Binary floating-point JSON numbers are forbidden, including finite floats,
  NaN, positive or negative Infinity, and negative zero. The integer token
  `-0` is also rejected rather than normalized to `0`.
- Scientific decimal values used in identity-bearing payloads are represented
  explicitly, for example:

  ```json
  {"numeric_type":"decimal_string","precision":50,"value":"1.25e-6"}
  ```

- Every object key is a unique NFC string.
- Every string value is already normalized to Unicode NFC. Implementations
  reject non-NFC input rather than normalizing it implicitly.
- Array order is semantic and is never changed.

## Byte Encoding

- Encode as UTF-8 without a byte order mark.
- Sort object keys in ascending Unicode code-point order.
- Emit no insignificant whitespace.
- Separate members with `,` and keys from values with `:`.
- Use lowercase JSON literals `true`, `false`, and `null`.
- Escape quotation mark, reverse solidus, and U+0000--U+001F as required by
  JSON. Do not escape other Unicode scalar values.
- Emit no final newline.

The reference implementation is
`sof_runtime.artifacts.canonical_json_bytes`. Cross-language implementations
must pass the canonical byte fixtures before their digests are accepted.
