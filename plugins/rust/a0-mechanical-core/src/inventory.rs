//! Exact flat inventory; no application acceptance, writers or scheduling.
#[cfg(windows)]
mod windows;
use crate::identity::{ByteLength, ContentDigest};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::path::Path;

pub type Result<T> = std::result::Result<T, Error>;
#[derive(Debug, Serialize)]
pub struct Error {
    pub class: &'static str,
    pub code: &'static str,
    pub detail: String,
}
impl Error {
    pub fn reject(code: &'static str, detail: impl Into<String>) -> Self {
        Self {
            class: "REJECTED",
            code,
            detail: detail.into(),
        }
    }
    pub fn unresolved(code: &'static str, detail: impl Into<String>) -> Self {
        Self {
            class: "INCOMPLETE",
            code,
            detail: detail.into(),
        }
    }
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Entry {
    pub name: String,
    pub kind: String,
    pub byte_length: ByteLength,
    pub sha256: ContentDigest,
}
pub fn validate_name(s: &str) -> Result<()> {
    if !s.is_ascii() {
        return Err(Error::reject("NAME", "ASCII filename required"));
    }
    let base = s.split('.').next().unwrap_or("").to_ascii_uppercase();
    let device = ["CON", "PRN", "AUX", "NUL", "CLOCK$", "CONIN$", "CONOUT$"]
        .contains(&base.as_str())
        || (base.len() == 4
            && ["COM", "LPT"].contains(&&base[..3])
            && (b'1'..=b'9').contains(&base.as_bytes()[3]));
    if s.is_empty()
        || s.len() > 255
        || s == "."
        || s == ".."
        || s.ends_with('.')
        || device
        || !s
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b"._-".contains(&b))
    {
        return Err(Error::reject(
            "NAME",
            "unsupported filename / device / ADS / escape",
        ));
    }
    Ok(())
}
pub fn validate_entries(entries: &[Entry]) -> Result<()> {
    let mut previous = "";
    let mut aliases = std::collections::BTreeSet::new();
    let mut total = 0u64;
    if entries.len() > 4096 {
        return Err(Error::unresolved("RESOURCE_LIMIT", "entry bound"));
    }
    for e in entries {
        validate_name(&e.name)?;
        if e.kind != "RegularFile"
            || e.name.as_str() <= previous
            || !aliases.insert(e.name.to_ascii_lowercase())
        {
            return Err(Error::reject(
                "ENTRY_ORDER_OR_ALIAS",
                "sorted unique regular filenames required",
            ));
        }
        total = total
            .checked_add(e.byte_length)
            .ok_or_else(|| Error::reject("LENGTH", "overflow"))?;
        previous = &e.name;
    }
    if total > 536870912 {
        return Err(Error::unresolved("RESOURCE_LIMIT", "total byte bound"));
    }
    Ok(())
}
#[cfg(windows)]
pub fn inspect(
    root: &Path,
    manifest: &Path,
    bindings: &Path,
    decode: &dyn Fn(&[u8], &[u8]) -> Result<Vec<Entry>>,
    hook: &mut dyn FnMut(&str) -> Result<()>,
) -> Result<Value> {
    use sha2::{Digest, Sha256};
    use std::io::{Read, Seek, SeekFrom};
    use windows::{Chain, Handle, Stamp};
    struct Control {
        handle: Handle,
        stamp: Stamp,
        chain: Chain,
        raw: Vec<u8>,
    }
    fn control(path: &Path) -> Result<Control> {
        let chain = Chain::new(
            path.parent()
                .ok_or_else(|| Error::reject("CONTROL_PATH", "missing parent"))?,
        )?;
        let mut handle = Handle::open(path, false)?;
        let stamp = handle.stamp()?;
        if stamp.length > 4194304 {
            return Err(Error::unresolved("RESOURCE_LIMIT", "control byte bound"));
        }
        let mut raw = Vec::new();
        handle
            .file
            .by_ref()
            .take(4194305)
            .read_to_end(&mut raw)
            .map_err(|e| Error::unresolved("READ", e.to_string()))?;
        if raw.len() as u64 != stamp.length {
            return Err(Error::unresolved("INPUT_CHANGED", "control length changed"));
        }
        Ok(Control {
            handle,
            stamp,
            chain,
            raw,
        })
    }
    fn hash(
        h: &mut Handle,
        length: u64,
        hook: &mut dyn FnMut(&str) -> Result<()>,
    ) -> Result<ContentDigest> {
        h.file
            .seek(SeekFrom::Start(0))
            .map_err(|e| Error::unresolved("READ", e.to_string()))?;
        let mut hash = Sha256::new();
        let mut buf = [0u8; 65536];
        let mut total = 0;
        loop {
            let n = h
                .file
                .read(&mut buf)
                .map_err(|e| Error::unresolved("READ", e.to_string()))?;
            if n == 0 {
                break;
            }
            hash.update(&buf[..n]);
            total += n as u64;
            hook("hashing")?;
            if total > length {
                return Err(Error::unresolved("INPUT_CHANGED", "file grew during read"));
            }
        }
        if total != length {
            return Err(Error::unresolved(
                "INPUT_CHANGED",
                "file shortened during read",
            ));
        }
        Ok(ContentDigest::from_hasher(hash))
    }
    if windows::within(manifest, root)? || windows::within(bindings, root)? {
        return Err(Error::reject(
            "CONTROL_INSIDE_ROOT",
            "detached controls required; self-reference forbidden",
        ));
    }
    let chain = Chain::new(root)?;
    let root_handle = Handle::open(root, true)?;
    let root_before = root_handle.stamp()?;
    let mut declaration = control(manifest)?;
    let mut expectation = control(bindings)?;
    let entries = decode(&declaration.raw, &expectation.raw)?;
    validate_entries(&entries)?;
    let expected_names: Vec<String> = entries.iter().map(|e| e.name.clone()).collect();
    let names = windows::names(root)?;
    if names != expected_names {
        return Err(Error::reject(
            "MEMBERSHIP",
            "missing or extra file; exact case-sensitive set required",
        ));
    }
    hook("enumerated")?;
    let mut files = Vec::new();
    let mut ids = std::collections::BTreeSet::new();
    for e in &entries {
        let h = Handle::open(&root.join(&e.name), false)?;
        let stamp = h.stamp()?;
        if stamp.length != e.byte_length {
            return Err(Error::reject("LENGTH", e.name.clone()));
        }
        if !ids.insert((stamp.volume, stamp.file_id)) {
            return Err(Error::reject("FILE_ALIAS", e.name.clone()));
        }
        files.push((h, stamp));
    }
    hook("opened")?;
    let mut observed = Vec::new();
    for ((h, stamp), e) in files.iter_mut().zip(&entries) {
        let digest = hash(h, stamp.length, hook)?;
        observed.push(Entry {
            name: e.name.clone(),
            kind: "RegularFile".into(),
            byte_length: stamp.length,
            sha256: digest,
        });
    }
    hook("after_hash")?;
    if windows::names(root).map_err(|_| Error::unresolved("INPUT_CHANGED", "membership changed"))?
        != names
    {
        return Err(Error::unresolved(
            "INPUT_CHANGED",
            "directory membership changed",
        ));
    }
    for ((h, stamp), e) in files.iter_mut().zip(&observed) {
        h.unchanged(stamp)?;
        if hash(h, stamp.length, &mut |_| Ok(()))? != e.sha256 {
            return Err(Error::unresolved("INPUT_CHANGED", "second read differs"));
        }
        h.unchanged(stamp)?;
    }
    for c in [&mut declaration, &mut expectation] {
        c.handle.unchanged(&c.stamp)?;
        c.chain.unchanged()?;
        c.handle
            .file
            .seek(SeekFrom::Start(0))
            .map_err(|e| Error::unresolved("READ", e.to_string()))?;
        let mut raw = Vec::new();
        c.handle
            .file
            .by_ref()
            .take(4194305)
            .read_to_end(&mut raw)
            .map_err(|e| Error::unresolved("READ", e.to_string()))?;
        if raw != c.raw {
            return Err(Error::unresolved("INPUT_CHANGED", "control bytes changed"));
        }
        c.handle.unchanged(&c.stamp)?;
    }
    root_handle.unchanged(&root_before)?;
    chain.unchanged()?;
    if observed != entries {
        return Err(Error::reject("DIGEST_MISMATCH", "declared content differs"));
    }
    let stamps: Vec<Value> = files
        .iter()
        .zip(&observed)
        .map(|((_, stamp), e)| json!({"name":e.name,"stamp":stamp}))
        .collect();
    let manifest_text = String::from_utf8(declaration.raw.clone()).unwrap();
    Ok(
        json!({"manifest_sha256":ContentDigest::of(&declaration.raw),"manifest_utf8":manifest_text,
        "bindings_sha256":ContentDigest::of(&expectation.raw),"entries":observed,"file_observations":stamps,
        "root_observation":root_before,"byte_passes":2,"backend":"windows-ntfs.v0"}),
    )
}
#[cfg(not(windows))]
pub fn inspect(
    _: &Path,
    _: &Path,
    _: &Path,
    _: &dyn Fn(&[u8], &[u8]) -> Result<Vec<Entry>>,
    _: &mut dyn FnMut(&str) -> Result<()>,
) -> Result<Value> {
    Err(Error::unresolved(
        "UNSUPPORTED_PLATFORM",
        "Windows NTFS v0 required",
    ))
}

#[cfg(windows)]
pub fn check_detached_path(
    path: &Path,
    root: &Path,
    manifest: &Path,
    bindings: &Path,
) -> Result<()> {
    let parent = path
        .parent()
        .ok_or_else(|| Error::reject("DETACHED_PATH", "path parent required"))?;
    let _chain = windows::Chain::new(parent)?;
    if windows::within(path, root)?
        || windows::key(path)? == windows::key(manifest)?
        || windows::key(path)? == windows::key(bindings)?
    {
        return Err(Error::reject("DETACHED_PATH", "path must be detached"));
    }
    validate_name(
        path.file_name()
            .and_then(|s| s.to_str())
            .ok_or_else(|| Error::reject("DETACHED_PATH", "path name"))?,
    )
}
#[cfg(not(windows))]
pub fn check_detached_path(_: &Path, _: &Path, _: &Path, _: &Path) -> Result<()> {
    Err(Error::unresolved(
        "UNSUPPORTED_PLATFORM",
        "Windows NTFS v0 required",
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn portable_names_reject_alias_forms() {
        for s in [
            "..",
            "CON",
            "con.txt",
            "LPT1.json",
            "x:stream",
            "x/y",
            "x\\y",
            "name.",
            "name ",
            "C:x",
            "\\\\server\\x",
        ] {
            assert!(validate_name(s).is_err(), "{s}");
        }
        assert!(validate_name("entry-123.bin").is_ok());
    }
}
