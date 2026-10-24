//! Application declaration profiles over one internal A0 mechanical library.
pub use a0_mechanical_core::inventory::Entry;
pub use a0_mechanical_core::{Error, Result, codec, identity, validate_name};
use identity::{
    CacheIdentity, CheckpointIdentity, ContentDigest, ExecutionIdentity, SourceIdentity,
};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::path::Path;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Producer {
    pub id: String,
    pub version: String,
    pub executable_sha256: ContentDigest,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CheckpointIdentities {
    pub source: SourceIdentity,
    pub execution: ExecutionIdentity,
    pub checkpoint: CheckpointIdentity,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CacheIdentities {
    pub source: SourceIdentity,
    pub execution: ExecutionIdentity,
    pub cache: CacheIdentity,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(untagged)]
pub enum Identities {
    Checkpoint(CheckpointIdentities),
    Cache(CacheIdentities),
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Schema {
    pub role: String,
    pub id: String,
    pub version: String,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Declarations {
    pub producer: Producer,
    pub identities: Identities,
    pub schemas: Vec<Schema>,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Manifest {
    pub schema: String,
    pub codec: String,
    pub declarations: Declarations,
    pub entries: Vec<Entry>,
}
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Bindings {
    schema: String,
    manifest_schema: String,
    codec: String,
    declarations: Declarations,
}
pub const SCHEMA: &str = "sof-runtime.a0-flat-inventory.v0";
pub const CACHE_SCHEMA: &str = "sof-runtime.a0-cache-flat-inventory.v0";
pub const CODEC: &str = "ascii-json-u64.v0";

fn decode<T: for<'a> Deserialize<'a>>(raw: &[u8]) -> Result<T> {
    serde_json::from_value(codec::parse(raw)?)
        .map_err(|e| Error::reject("DECLARATION", e.to_string()))
}
pub fn declarations(raw: &[u8], expected: &[u8]) -> Result<Manifest> {
    let m: Manifest = decode(raw)?;
    let b: Bindings = decode(expected)?;
    let profile = match (&*m.schema, &m.declarations.identities) {
        (SCHEMA, Identities::Checkpoint(_)) => "sof-runtime.a0-inspection-bindings.v0",
        (CACHE_SCHEMA, Identities::Cache(_)) => "sof-runtime.a0-cache-inspection-bindings.v0",
        _ => return Err(Error::reject("VERSION", "schema/identity profile mismatch")),
    };
    if m.codec != CODEC || b.schema != profile || b.manifest_schema != m.schema || b.codec != CODEC
    {
        return Err(Error::reject("VERSION", "unsupported schema/codec"));
    }
    if m.declarations != b.declarations {
        return Err(Error::reject(
            "BINDING_MISMATCH",
            "producer/schema/identity declarations differ",
        ));
    }
    if m.declarations.producer.id.is_empty() || m.declarations.producer.version.is_empty() {
        return Err(Error::reject("DECLARATION", "producer id/version required"));
    }
    let mut previous = "";
    for s in &m.declarations.schemas {
        if s.role.as_str() <= previous || s.id.is_empty() || s.version.is_empty() {
            return Err(Error::reject(
                "SCHEMA_BINDING",
                "unique sorted schema roles required",
            ));
        }
        previous = &s.role;
    }
    a0_mechanical_core::inventory::validate_entries(&m.entries)?;
    Ok(m)
}

pub fn inspect(
    root: &Path,
    manifest: &Path,
    bindings: &Path,
    hook: &mut dyn FnMut(&str) -> Result<()>,
) -> Result<Value> {
    a0_mechanical_core::inventory::inspect(
        root,
        manifest,
        bindings,
        &|raw, expected| Ok(declarations(raw, expected)?.entries),
        hook,
    )
}

pub fn check_marker(marker: &Path, root: &Path, manifest: &Path, bindings: &Path) -> Result<()> {
    a0_mechanical_core::inventory::check_detached_path(marker, root, manifest, bindings).map_err(
        |e| {
            if e.code == "DETACHED_PATH" {
                let detail = match e.detail.as_str() {
                    "path parent required" => "marker parent required",
                    "path must be detached" => "test marker must be detached",
                    _ => "marker name",
                };
                Error::reject("FAULT_PATH", detail)
            } else {
                e
            }
        },
    )
}
