# Internal A0 Mechanical Core

Experimental library, `publish = false`. Exactly three top-level modules:
`identity`, `codec`, `inventory`. The private NTFS backend belongs to inventory.

The [extraction review](../../../docs/internal/SHARED_A0_EXTRACTION_REVIEW_V0.md)
and [SOF guard](../../../docs/internal/SOF_COMPATIBILITY_GUARD_V0.md) own scope.
Both read-only shadows use this library through the inspector's path dependency;
application declaration profiles remain in that executable's adapter library.

```powershell
cargo test --locked --offline --manifest-path plugins/rust/a0-mechanical-core/Cargo.toml
```

Identity constructors are explicit declarations, not authentication. The codec
accepts only printable ASCII metadata, u64, bool/null, arrays and objects, with
exact canonical bytes. Existing application/SOF files stay opaque raw bytes.
Inventory accepts only declared single-level regular-file sets on supported
local Windows NTFS and reports an observation interval, not future permission.

No application PASS, source approval, cache policy, checkpoint inheritance,
writer, lock, process supervisor or publication lifecycle is implemented here.
This is not an installed public runtime API or a production-path migration.
