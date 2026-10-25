use crate::{Error, Result, validate_name};
use serde::Serialize;
use std::ffi::c_void;
use std::fs::File;
use std::os::windows::io::{AsRawHandle, FromRawHandle};
use std::path::{Path, PathBuf};

#[repr(C)]
#[derive(Default)]
struct Time {
    low: u32,
    high: u32,
}
#[repr(C)]
#[derive(Default)]
struct Info {
    attributes: u32,
    created: Time,
    accessed: Time,
    written: Time,
    volume: u32,
    size_high: u32,
    size_low: u32,
    links: u32,
    index_high: u32,
    index_low: u32,
}
#[link(name = "kernel32")]
unsafe extern "system" {
    fn CreateFileW(
        name: *const u16,
        access: u32,
        share: u32,
        security: *const c_void,
        creation: u32,
        flags: u32,
        template: *mut c_void,
    ) -> *mut c_void;
    fn GetFileInformationByHandle(handle: *mut c_void, info: *mut Info) -> i32;
    fn GetFileInformationByHandleEx(
        handle: *mut c_void,
        class: u32,
        info: *mut c_void,
        size: u32,
    ) -> i32;
    fn GetFinalPathNameByHandleW(handle: *mut c_void, name: *mut u16, size: u32, flags: u32)
    -> u32;
    fn GetVolumeInformationByHandleW(
        handle: *mut c_void,
        volume: *mut u16,
        size: u32,
        serial: *mut u32,
        component: *mut u32,
        flags: *mut u32,
        filesystem: *mut u16,
        filesystem_size: u32,
    ) -> i32;
}
fn os_error() -> Error {
    Error::unresolved("OS_METADATA", std::io::Error::last_os_error().to_string())
}
fn full(high: u32, low: u32) -> u64 {
    ((high as u64) << 32) | low as u64
}
pub fn key(path: &Path) -> Result<String> {
    let s = path
        .to_str()
        .ok_or_else(|| Error::reject("ROOT_PATH", "ASCII local drive path required"))?;
    let s = s.strip_prefix(r"\\?\").unwrap_or(s);
    if !s.is_ascii()
        || s.len() < 3
        || !s.as_bytes()[0].is_ascii_alphabetic()
        || &s[1..3] != ":\\"
        || s.contains('/')
        || s.len() > 16000
    {
        return Err(Error::reject("ROOT_PATH", "unsupported absolute path"));
    }
    for part in s[3..].split('\\') {
        if part.is_empty() && s.len() == 3 {
            continue;
        }
        if part.is_empty()
            || part == "."
            || part == ".."
            || part.ends_with(['.', ' '])
            || part.bytes().any(|b| b < 32 || b"/:*?\"<>|".contains(&b))
            || device(part)
        {
            return Err(Error::reject("ROOT_PATH", "unsafe path component"));
        }
    }
    Ok(s.to_ascii_lowercase())
}
pub fn device(name: &str) -> bool {
    let base = name.split('.').next().unwrap_or("").to_ascii_uppercase();
    ["CON", "PRN", "AUX", "NUL", "CLOCK$", "CONIN$", "CONOUT$"].contains(&base.as_str())
        || (base.len() == 4
            && ["COM", "LPT"].contains(&&base[..3])
            && (b'1'..=b'9').contains(&base.as_bytes()[3]))
}
pub fn within(path: &Path, root: &Path) -> Result<bool> {
    let p = key(path)?;
    let r = key(root)?;
    Ok(p == r || p.starts_with(&(r.trim_end_matches('\\').to_string() + "\\")))
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct Stamp {
    pub volume: u32,
    pub file_id: u64,
    pub length: u64,
    pub links: u32,
    pub attributes: u32,
    pub created: u64,
    pub written: u64,
    pub streams: Vec<(String, u64)>,
}
impl Stamp {
    fn identity(&self) -> (u32, u64) {
        (self.volume, self.file_id)
    }
}

pub struct Handle {
    pub file: File,
    pub path: PathBuf,
    directory: bool,
}
impl Handle {
    pub fn open(path: &Path, directory: bool) -> Result<Self> {
        key(path)?;
        let s = path
            .to_str()
            .unwrap()
            .strip_prefix(r"\\?\")
            .unwrap_or(path.to_str().unwrap());
        let wide: Vec<u16> = format!(r"\\?\{s}").encode_utf16().chain([0]).collect();
        // OPEN_EXISTING + read-only access, no final reparse traversal. Sharing
        // permits controlled mutation tests; no locking or publisher is implemented.
        let h = unsafe {
            CreateFileW(
                wide.as_ptr(),
                0x80000000,
                7,
                std::ptr::null(),
                3,
                0x02200000,
                std::ptr::null_mut(),
            )
        };
        if h as isize == -1 {
            return Err(os_error());
        }
        let file = unsafe { File::from_raw_handle(h) };
        let out = Self {
            file,
            path: path.to_path_buf(),
            directory,
        };
        out.stamp()?;
        let mut final_name = vec![0u16; 32768];
        let n = unsafe {
            GetFinalPathNameByHandleW(
                out.file.as_raw_handle(),
                final_name.as_mut_ptr(),
                final_name.len() as u32,
                0,
            )
        };
        if n == 0 || n as usize >= final_name.len() {
            return Err(os_error());
        }
        let actual = String::from_utf16(&final_name[..n as usize])
            .map_err(|_| Error::reject("PATH_ALIAS", "non-ASCII path"))?;
        if key(Path::new(&actual))? != key(path)? {
            return Err(Error::reject(
                "PATH_ALIAS",
                "normalized handle path differs",
            ));
        }
        Ok(out)
    }
    pub fn ntfs(&self) -> Result<()> {
        let mut name = [0u16; 64];
        let mut flags = 0;
        let ok = unsafe {
            GetVolumeInformationByHandleW(
                self.file.as_raw_handle(),
                std::ptr::null_mut(),
                0,
                std::ptr::null_mut(),
                std::ptr::null_mut(),
                &mut flags,
                name.as_mut_ptr(),
                name.len() as u32,
            )
        };
        if ok == 0 {
            return Err(os_error());
        }
        let end = name.iter().position(|x| *x == 0).unwrap_or(name.len());
        if String::from_utf16_lossy(&name[..end]) != "NTFS" || flags & 0x40000 == 0 {
            return Err(Error::unresolved(
                "UNSUPPORTED_FILESYSTEM",
                "local NTFS stream metadata required",
            ));
        }
        Ok(())
    }
    pub fn stamp(&self) -> Result<Stamp> {
        let mut info = Info::default();
        if unsafe { GetFileInformationByHandle(self.file.as_raw_handle(), &mut info) } == 0 {
            return Err(os_error());
        }
        if info.attributes & 0x400 != 0 {
            return Err(Error::reject(
                "REPARSE_POINT",
                "reparse objects not admitted",
            ));
        }
        if (info.attributes & 0x10 != 0) != self.directory || info.attributes & 0x40 != 0 {
            return Err(Error::reject(
                "FILE_TYPE",
                "directory/regular-file mismatch",
            ));
        }
        if !self.directory && info.links != 1 {
            return Err(Error::reject(
                "HARD_LINK",
                "one name per regular file required",
            ));
        }
        let streams = self.streams()?;
        if streams.iter().any(|(name, _)| name != "::$DATA")
            || (!self.directory && streams.len() != 1)
        {
            return Err(Error::reject(
                "NAMED_STREAM",
                "only the unnamed data stream is admitted",
            ));
        }
        if !self.directory && streams[0].1 != full(info.size_high, info.size_low) {
            return Err(Error::unresolved(
                "INPUT_CHANGED",
                "stream/file lengths disagree",
            ));
        }
        Ok(Stamp {
            volume: info.volume,
            file_id: full(info.index_high, info.index_low),
            length: full(info.size_high, info.size_low),
            links: info.links,
            attributes: info.attributes,
            created: full(info.created.high, info.created.low),
            written: full(info.written.high, info.written.low),
            streams,
        })
    }
    fn streams(&self) -> Result<Vec<(String, u64)>> {
        let mut buffer = vec![0u64; 8192];
        let ok = unsafe {
            GetFileInformationByHandleEx(
                self.file.as_raw_handle(),
                7,
                buffer.as_mut_ptr().cast(),
                (buffer.len() * 8) as u32,
            )
        };
        if ok == 0 {
            let e = std::io::Error::last_os_error();
            if self.directory && e.raw_os_error() == Some(38) {
                return Ok(Vec::new());
            }
            return Err(Error::unresolved("STREAM_METADATA", e.to_string()));
        }
        let bytes =
            unsafe { std::slice::from_raw_parts(buffer.as_ptr().cast::<u8>(), buffer.len() * 8) };
        let mut offset = 0;
        let mut out = Vec::new();
        loop {
            if offset + 24 > bytes.len() {
                return Err(Error::unresolved(
                    "STREAM_METADATA",
                    "truncated stream record",
                ));
            }
            let next = u32::from_le_bytes(bytes[offset..offset + 4].try_into().unwrap()) as usize;
            let length =
                u32::from_le_bytes(bytes[offset + 4..offset + 8].try_into().unwrap()) as usize;
            let size = i64::from_le_bytes(bytes[offset + 8..offset + 16].try_into().unwrap());
            if length == 0
                || length % 2 != 0
                || offset + 24 + length > bytes.len()
                || size < 0
                || out.len() > 256
            {
                return Err(Error::unresolved(
                    "STREAM_METADATA",
                    "invalid stream record",
                ));
            }
            let units: Vec<u16> = bytes[offset + 24..offset + 24 + length]
                .chunks_exact(2)
                .map(|b| u16::from_le_bytes([b[0], b[1]]))
                .collect();
            let name = String::from_utf16(&units)
                .map_err(|_| Error::unresolved("STREAM_METADATA", "invalid stream name"))?;
            out.push((name, size as u64));
            if next == 0 {
                break;
            }
            if next % 8 != 0 || next < 24 + length {
                return Err(Error::unresolved(
                    "STREAM_METADATA",
                    "invalid stream offset",
                ));
            }
            offset += next;
        }
        out.sort();
        Ok(out)
    }
    pub fn unchanged(&self, before: &Stamp) -> Result<()> {
        let now = self
            .stamp()
            .map_err(|_| Error::unresolved("INPUT_CHANGED", "held object metadata changed"))?;
        let path = Self::open(&self.path, self.directory).map_err(|_| {
            Error::unresolved(
                "INPUT_CHANGED",
                "path no longer resolves to the checked object",
            )
        })?;
        if &now != before || path.stamp()? != *before {
            return Err(Error::unresolved(
                "INPUT_CHANGED",
                "handle/path identity or metadata changed",
            ));
        }
        Ok(())
    }
}

pub struct Chain {
    handles: Vec<(Handle, Stamp)>,
}
impl Chain {
    pub fn new(root: &Path) -> Result<Self> {
        key(root)?;
        let paths: Vec<&Path> = root.ancestors().collect();
        let mut handles = Vec::new();
        for p in paths.into_iter().rev() {
            let h = Handle::open(p, true)?;
            let s = h.stamp()?;
            handles.push((h, s));
        }
        handles.last().unwrap().0.ntfs()?;
        Ok(Self { handles })
    }
    pub fn unchanged(&self) -> Result<()> {
        for (h, s) in &self.handles {
            let current = Handle::open(&h.path, true)
                .map_err(|_| Error::unresolved("INPUT_CHANGED", "ancestor changed"))?;
            if h.stamp()?.identity() != s.identity() || current.stamp()?.identity() != s.identity()
            {
                return Err(Error::unresolved(
                    "INPUT_CHANGED",
                    "ancestor identity changed",
                ));
            }
        }
        Ok(())
    }
}

pub fn names(root: &Path) -> Result<Vec<String>> {
    let mut out = Vec::new();
    let mut aliases = std::collections::BTreeSet::new();
    for item in
        std::fs::read_dir(root).map_err(|e| Error::unresolved("ENUMERATION", e.to_string()))?
    {
        let name = item
            .map_err(|e| Error::unresolved("ENUMERATION", e.to_string()))?
            .file_name()
            .into_string()
            .map_err(|_| Error::reject("NAME", "ASCII name required"))?;
        validate_name(&name)?;
        if !aliases.insert(name.to_ascii_lowercase()) {
            return Err(Error::reject("NAME_ALIAS", "case alias"));
        }
        out.push(name);
        if out.len() > 4096 {
            return Err(Error::unresolved("RESOURCE_LIMIT", "entry bound"));
        }
    }
    out.sort();
    Ok(out)
}
