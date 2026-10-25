use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fs::{self, File, OpenOptions, TryLockError};
use std::io::{BufReader, Read, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, ExitCode, Stdio};
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

type Outcome<T> = Result<T, String>;
const MAX_I64: u64 = i64::MAX as u64;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Request {
    schema: String,
    cache_root: PathBuf,
    identity: Value,
    source_paths: BTreeMap<String, PathBuf>,
    preparer_paths: BTreeMap<String, PathBuf>,
    builder_program: PathBuf,
    working_directory: PathBuf,
    invalid_policy: String,
    lock_timeout_seconds: u64,
    build_timeout_seconds: u64,
    consumer: Option<Consumer>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Consumer {
    program: PathBuf,
    sha256: String,
    args: Vec<String>,
    timeout_seconds: u64,
}

#[derive(Debug)]
struct Failure {
    status: &'static str,
    detail: String,
}

fn fail(status: &'static str, detail: impl ToString) -> Failure {
    Failure {
        status,
        detail: detail.to_string(),
    }
}

fn hash_file(path: &Path) -> Outcome<(u64, String)> {
    let mut file = File::open(path).map_err(|e| e.to_string())?;
    let mut digest = Sha256::new();
    let mut length = 0u64;
    let mut buffer = vec![0; 1024 * 1024];
    loop {
        let count = file.read(&mut buffer).map_err(|e| e.to_string())?;
        if count == 0 {
            break;
        }
        digest.update(&buffer[..count]);
        length += count as u64;
    }
    Ok((length, format!("{:x}", digest.finalize())))
}

fn canonical(value: &Value) -> Vec<u8> {
    serde_json::to_vec(value).expect("JSON value serialization")
}

fn identity_key(identity: &Value) -> String {
    format!("{:x}", Sha256::digest(canonical(identity)))
}

fn field<'a>(value: &'a Value, key: &str) -> Outcome<&'a Value> {
    value.get(key).ok_or_else(|| format!("missing field {key}"))
}

fn text<'a>(value: &'a Value, key: &str) -> Outcome<&'a str> {
    field(value, key)?
        .as_str()
        .ok_or_else(|| format!("invalid string {key}"))
}

fn integer(value: &Value, key: &str) -> Outcome<u64> {
    field(value, key)?
        .as_u64()
        .ok_or_else(|| format!("invalid unsigned integer {key}"))
}

fn valid_header(header: &Value) -> Outcome<()> {
    let keys = [
        "schema",
        "source_field",
        "source_identity",
        "sign_semantics",
        "sector_labels",
        "record_count",
        "source_artifacts",
    ];
    let object = header.as_object().ok_or("header object")?;
    if object.len() != keys.len() || keys.iter().any(|key| !object.contains_key(*key)) {
        return Err("header has missing or extra fields".into());
    }
    for key in ["source_field", "source_identity", "sign_semantics"] {
        if text(header, key)?.is_empty() {
            return Err("empty header string".into());
        }
    }
    let labels = header["sector_labels"].as_array().ok_or("sector labels")?;
    let mut unique = BTreeSet::new();
    for label in labels {
        let label = label
            .as_str()
            .filter(|label| !label.is_empty())
            .ok_or("sector label type/length")?;
        if !unique.insert(label) {
            return Err("duplicate sector label".into());
        }
    }
    if labels.is_empty()
        || labels.len() > u16::MAX as usize
        || integer(header, "record_count")? > MAX_I64
    {
        return Err("header bounds".into());
    }
    Ok(())
}

fn verify_sources(request: &Request) -> Result<(), Failure> {
    let sources = request.identity["sources"]
        .as_array()
        .ok_or_else(|| fail("INVALID_REQUEST", "sources must be an array"))?;
    if sources.len() != request.source_paths.len() || sources.is_empty() {
        return Err(fail("INVALID_REQUEST", "source role cardinality mismatch"));
    }
    let mut roles = BTreeSet::new();
    for source in sources {
        let role = text(source, "role").map_err(|e| fail("INVALID_REQUEST", e))?;
        if !roles.insert(role) {
            return Err(fail("INVALID_REQUEST", "duplicate source role"));
        }
        let path = request
            .source_paths
            .get(role)
            .ok_or_else(|| fail("INVALID_REQUEST", "missing source path"))?;
        let (length, digest) = hash_file(path).map_err(|e| fail("SOURCE_IDENTITY_REJECTED", e))?;
        if Some(length) != source["size"].as_u64()
            || Some(digest.as_str()) != source["sha256"].as_str()
            || path.file_name().and_then(|s| s.to_str()) != source["name"].as_str()
        {
            return Err(fail("SOURCE_IDENTITY_REJECTED", role));
        }
    }
    let preparer = &request.identity["preparer"];
    let (_, executable_digest) =
        hash_file(&request.builder_program).map_err(|e| fail("PREPARER_IDENTITY_REJECTED", e))?;
    if Some(executable_digest.as_str()) != preparer["executable_sha256"].as_str() {
        return Err(fail("PREPARER_IDENTITY_REJECTED", "interpreter digest"));
    }
    let closure = preparer["sources_sha256"]
        .as_object()
        .ok_or_else(|| fail("INVALID_REQUEST", "preparer closure"))?;
    if closure.len() != request.preparer_paths.len() || closure.is_empty() {
        return Err(fail("INVALID_REQUEST", "preparer closure cardinality"));
    }
    for (name, expected) in closure {
        let path = request
            .preparer_paths
            .get(name)
            .ok_or_else(|| fail("INVALID_REQUEST", "missing preparer source path"))?;
        let (_, digest) = hash_file(path).map_err(|e| fail("PREPARER_IDENTITY_REJECTED", e))?;
        if expected.as_str() != Some(digest.as_str()) {
            return Err(fail("PREPARER_IDENTITY_REJECTED", name));
        }
    }
    Ok(())
}

fn regular(path: &Path) -> Outcome<()> {
    let metadata = fs::symlink_metadata(path).map_err(|e| e.to_string())?;
    if !metadata.file_type().is_file() {
        return Err("not a regular file".into());
    }
    Ok(())
}

fn read_bytes<const N: usize>(reader: &mut impl Read) -> Outcome<[u8; N]> {
    let mut bytes = [0; N];
    reader.read_exact(&mut bytes).map_err(|e| e.to_string())?;
    Ok(bytes)
}

#[derive(Serialize, Deserialize, PartialEq, Debug)]
#[serde(deny_unknown_fields)]
struct Packet {
    name: String,
    size: u64,
    sha256: String,
    header: Value,
    record_count: u64,
    edge_count: u64,
}

fn validate_packet(path: &Path, identity: &Value) -> Outcome<Packet> {
    regular(path)?;
    let (size, sha256) = hash_file(path)?;
    let mut reader = BufReader::new(File::open(path).map_err(|e| e.to_string())?);
    if &read_bytes::<8>(&mut reader)? != b"RIMEPC01" {
        return Err("packet magic".into());
    }
    let length = u32::from_le_bytes(read_bytes::<4>(&mut reader)?) as usize;
    if length == 0 || length > 1_000_000 {
        return Err("packet header length".into());
    }
    let mut raw = vec![0; length];
    reader.read_exact(&mut raw).map_err(|e| e.to_string())?;
    let header: Value = serde_json::from_slice(&raw).map_err(|e| e.to_string())?;
    if canonical(&header) != raw || header != identity["expected_header"] {
        return Err("packet header differs from canonical identity header".into());
    }
    let count = integer(&header, "record_count")?;
    let sectors = field(&header, "sector_labels")?
        .as_array()
        .ok_or("sector labels")?
        .len();
    if count > MAX_I64 || sectors == 0 || sectors > u16::MAX as usize {
        return Err("header bounds".into());
    }
    let mut previous = None;
    let mut edges = 0u64;
    for _ in 0..count {
        let source = u64::from_le_bytes(read_bytes::<8>(&mut reader)?);
        let sector = u16::from_le_bytes(read_bytes::<2>(&mut reader)?) as usize;
        let sign = i8::from_le_bytes(read_bytes::<1>(&mut reader)?);
        let edge_count = u32::from_le_bytes(read_bytes::<4>(&mut reader)?);
        if source > MAX_I64
            || previous.is_some_and(|p| source <= p)
            || sector >= sectors
            || !matches!(sign, -1 | 1)
            || edge_count == 0
        {
            return Err("source record bounds/order".into());
        }
        previous = Some(source);
        edges = edges
            .checked_add(u64::from(edge_count))
            .ok_or("edge count overflow")?;
        let mut mass = 0u64;
        for _ in 0..edge_count {
            let target = u16::from_le_bytes(read_bytes::<2>(&mut reader)?) as usize;
            let weight = u64::from_le_bytes(read_bytes::<8>(&mut reader)?);
            if target >= sectors || weight == 0 || weight > MAX_I64 {
                return Err("edge bounds".into());
            }
            mass = mass
                .checked_add(weight)
                .filter(|v| *v <= MAX_I64)
                .ok_or("row mass overflow")?;
        }
    }
    let mut tail = [0; 1];
    if reader.read(&mut tail).map_err(|e| e.to_string())? != 0 {
        return Err("trailing bytes".into());
    }
    if edges != integer(identity, "expected_edge_count")? {
        return Err("edge cardinality".into());
    }
    Ok(Packet {
        name: "packet.bin".into(),
        size,
        sha256,
        header,
        record_count: count,
        edge_count: edges,
    })
}

fn validate_entry(entry: &Path, identity: &Value, key: &str) -> Outcome<Packet> {
    let meta = fs::symlink_metadata(entry).map_err(|e| e.to_string())?;
    if !meta.file_type().is_dir() {
        return Err("entry is not a regular directory".into());
    }
    let manifest_path = entry.join("manifest.json");
    regular(&manifest_path)?;
    if fs::metadata(&manifest_path)
        .map_err(|e| e.to_string())?
        .len()
        > 1_000_000
    {
        return Err("manifest too large".into());
    }
    let raw = fs::read(&manifest_path).map_err(|e| e.to_string())?;
    let manifest: Value = serde_json::from_slice(&raw).map_err(|e| e.to_string())?;
    if raw != canonical(&manifest)
        || manifest["schema"] != "sof-runtime.prepared-input-manifest.v1"
        || manifest["key"] != key
        || manifest["identity"] != *identity
    {
        return Err("manifest schema/key/identity/canonical encoding".into());
    }
    let packet = validate_packet(&entry.join("packet.bin"), identity)?;
    let expected: Packet =
        serde_json::from_value(manifest["packet"].clone()).map_err(|e| e.to_string())?;
    if packet != expected {
        return Err("packet length/digest/protocol differs from manifest".into());
    }
    Ok(packet)
}

fn token() -> String {
    format!(
        "{}.{}",
        std::process::id(),
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    )
}

fn process(
    program: &Path,
    args: &[String],
    directory: &Path,
    timeout: u64,
) -> Outcome<(String, String)> {
    let mut command = Command::new(program);
    command
        .args(args)
        .current_dir(directory)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    command
        .env_remove("PYTHONOPTIMIZE")
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .env("PYTHONHASHSEED", "0");
    for key in [
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
        "RAYON_NUM_THREADS",
    ] {
        command.env(key, "1");
    }
    let mut child = command.spawn().map_err(|e| e.to_string())?;
    let stdout = child.stdout.take().ok_or("stdout pipe")?;
    let stderr = child.stderr.take().ok_or("stderr pipe")?;
    let capture = |stream: Box<dyn Read + Send>| {
        thread::spawn(move || {
            let mut bytes = Vec::new();
            stream
                .take(1_048_577)
                .read_to_end(&mut bytes)
                .map_err(|e| e.to_string())?;
            if bytes.len() > 1_048_576 {
                return Err("child output limit".to_string());
            }
            String::from_utf8(bytes).map_err(|e| e.to_string())
        })
    };
    let out = capture(Box::new(stdout));
    let err = capture(Box::new(stderr));
    let started = Instant::now();
    let status = loop {
        match child.try_wait().map_err(|e| e.to_string())? {
            Some(status) => break Ok(status),
            None if started.elapsed() > Duration::from_secs(timeout) => {
                let _ = child.kill();
                let _ = child.wait();
                break Err("child execution timeout".to_string());
            }
            None => thread::sleep(Duration::from_millis(5)),
        }
    };
    let output = out.join().map_err(|_| "stdout reader panicked")??;
    let error = err.join().map_err(|_| "stderr reader panicked")??;
    if !status?.success() {
        return Err(format!("child failed: {error}"));
    }
    Ok((output, error))
}

fn builder_args(request: &Request, output: &Path) -> Outcome<Vec<String>> {
    let args = request.identity["preparer"]["command"]
        .as_array()
        .ok_or("builder command")?;
    let mut output_count = 0;
    let mut resolved = Vec::new();
    for argument in args {
        let value = argument.as_str().ok_or("builder command argument")?;
        if value == "{output}" {
            output_count += 1;
            resolved.push(output.to_string_lossy().into_owned());
        } else if value.starts_with("{source:") && value.ends_with('}') {
            let role = &value[8..value.len() - 1];
            resolved.push(
                request
                    .source_paths
                    .get(role)
                    .ok_or("source placeholder")?
                    .to_string_lossy()
                    .into_owned(),
            );
        } else {
            resolved.push(value.to_string());
        }
    }
    if output_count != 1 {
        return Err("builder must contain exactly one output placeholder".into());
    }
    Ok(resolved)
}

fn execute(request: Request) -> Result<Value, Failure> {
    let started = Instant::now();
    if request.schema != "sof-runtime.prepared-input-cache-request.v1"
        || request.identity["schema"] != "sof-runtime.prepared-input-identity.v1"
        || !matches!(request.invalid_policy.as_str(), "reject" | "rebuild")
        || !(1..=600).contains(&request.lock_timeout_seconds)
        || !(1..=600).contains(&request.build_timeout_seconds)
        || request.identity["packet_format"]["schema"] != "rime.malecns.profile-census-input.v1"
        || request.identity["packet_format"]["magic"] != "RIMEPC01"
        || request.identity["packet_format"]["byte_order"] != "little"
        || request.identity["packet_format"]["version"] != 1
    {
        return Err(fail("INVALID_REQUEST", "schema/policy/limits/format"));
    }
    for name in [
        "sector_policy",
        "sign_policy",
        "expected_header",
        "preparer",
    ] {
        if !request.identity[name].is_object() {
            return Err(fail("INVALID_REQUEST", name));
        }
    }
    valid_header(&request.identity["expected_header"]).map_err(|e| fail("INVALID_REQUEST", e))?;
    for name in ["sector_policy", "sign_policy", "preparer"] {
        for key in ["id", "version"] {
            if request.identity[name][key]
                .as_str()
                .is_none_or(str::is_empty)
            {
                return Err(fail("INVALID_REQUEST", format!("{name}.{key}")));
            }
        }
    }
    if !request.identity["sign_policy"]["mapping"].is_object()
        || !request.identity["preparer"]["runtime"].is_object()
        || !request.identity["preparer"]["command"].is_array()
        || request.identity["expected_header"]["source_field"]
            != request.identity["sector_policy"]["field"]
        || request.identity["expected_header"]["sign_semantics"]
            != request.identity["sign_policy"]["id"]
    {
        return Err(fail(
            "INVALID_REQUEST",
            "policy/runtime/command declaration",
        ));
    }
    if request.identity["expected_header"]["schema"] != request.identity["packet_format"]["schema"]
        || request.identity["expected_header"]["source_artifacts"] != request.identity["sources"]
    {
        return Err(fail("INVALID_REQUEST", "header/source/format binding"));
    }
    let verify_started = Instant::now();
    verify_sources(&request)?;
    let mut timings = BTreeMap::<String, f64>::new();
    timings.insert(
        "initial_source_preparer_verification_seconds".into(),
        verify_started.elapsed().as_secs_f64(),
    );
    let key = identity_key(&request.identity);
    fs::create_dir_all(&request.cache_root).map_err(|e| fail("CACHE_IO_FAILED", e))?;
    let root = request
        .cache_root
        .canonicalize()
        .map_err(|e| fail("CACHE_IO_FAILED", e))?;
    for name in ["entries", "locks", "staging", "quarantine"] {
        fs::create_dir_all(root.join(name)).map_err(|e| fail("CACHE_IO_FAILED", e))?;
    }
    let lock_started = Instant::now();
    let lock = OpenOptions::new()
        .read(true)
        .write(true)
        .create(true)
        .truncate(false)
        .open(root.join("locks").join(format!("{key}.lock")))
        .map_err(|e| fail("CACHE_IO_FAILED", e))?;
    loop {
        match lock.try_lock() {
            Ok(()) => break,
            Err(TryLockError::WouldBlock)
                if lock_started.elapsed() < Duration::from_secs(request.lock_timeout_seconds) =>
            {
                thread::sleep(Duration::from_millis(10))
            }
            Err(TryLockError::WouldBlock) => {
                return Err(fail("CACHE_LOCK_TIMEOUT", "key is still locked"));
            }
            Err(TryLockError::Error(error)) => return Err(fail("CACHE_IO_FAILED", error)),
        }
    }
    timings.insert(
        "lock_wait_seconds".into(),
        lock_started.elapsed().as_secs_f64(),
    );
    let entry = root.join("entries").join(&key);
    let validation_started = Instant::now();
    let exists = match fs::symlink_metadata(&entry) {
        Ok(_) => true,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => false,
        Err(error) => return Err(fail("CACHE_IO_FAILED", error)),
    };
    let existing = if exists {
        Some(validate_entry(&entry, &request.identity, &key))
    } else {
        None
    };
    timings.insert(
        "existing_entry_validation_seconds".into(),
        validation_started.elapsed().as_secs_f64(),
    );
    let mut invalid_reason = None;
    let mut quarantine = None;
    let (status, packet) = match existing {
        Some(Ok(packet)) => ("CACHE_HIT_VALIDATED", packet),
        other => {
            if let Some(Err(reason)) = other {
                if request.invalid_policy == "reject" {
                    return Err(fail("CACHE_INVALID_REJECTED", reason));
                }
                invalid_reason = Some(reason);
                let destination = root.join("quarantine").join(format!("{key}.{}", token()));
                fs::rename(&entry, &destination).map_err(|e| fail("CACHE_IO_FAILED", e))?;
                quarantine = Some(
                    destination
                        .file_name()
                        .unwrap()
                        .to_string_lossy()
                        .into_owned(),
                );
            }
            let stage = root.join("staging").join(format!("{key}.{}", token()));
            fs::create_dir(&stage).map_err(|e| fail("CACHE_IO_FAILED", e))?;
            let packet_path = stage.join("packet.bin");
            let args =
                builder_args(&request, &packet_path).map_err(|e| fail("INVALID_REQUEST", e))?;
            let build_started = Instant::now();
            process(
                &request.builder_program,
                &args,
                &request.working_directory,
                request.build_timeout_seconds,
            )
            .map_err(|e| fail("CACHE_BUILD_FAILED", e))?;
            timings.insert(
                "preparation_seconds".into(),
                build_started.elapsed().as_secs_f64(),
            );
            let new_started = Instant::now();
            let packet = validate_packet(&packet_path, &request.identity)
                .map_err(|e| fail("CACHE_BUILD_FAILED", e))?;
            verify_sources(&request)?;
            OpenOptions::new()
                .read(true)
                .write(true)
                .open(&packet_path)
                .and_then(|file| file.sync_all())
                .map_err(|e| fail("CACHE_IO_FAILED", e))?;
            let manifest = json!({"schema":"sof-runtime.prepared-input-manifest.v1", "key":key,
                                  "identity":request.identity, "packet":packet});
            let mut file = File::create_new(stage.join("manifest.json"))
                .map_err(|e| fail("CACHE_IO_FAILED", e))?;
            file.write_all(&canonical(&manifest))
                .and_then(|_| file.sync_all())
                .map_err(|e| fail("CACHE_IO_FAILED", e))?;
            drop(file);
            fs::rename(&stage, &entry).map_err(|e| fail("CACHE_IO_FAILED", e))?;
            timings.insert(
                "new_packet_validation_publication_seconds".into(),
                new_started.elapsed().as_secs_f64(),
            );
            (
                if invalid_reason.is_some() {
                    "CACHE_INVALID_REBUILT"
                } else {
                    "CACHE_MISS_PREPARED"
                },
                packet,
            )
        }
    };
    let consumer_result = if let Some(consumer) = &request.consumer {
        if !(1..=600).contains(&consumer.timeout_seconds) {
            return Err(fail("INVALID_REQUEST", "consumer timeout"));
        }
        if consumer
            .args
            .iter()
            .filter(|arg| arg.as_str() == "{packet}")
            .count()
            != 1
        {
            return Err(fail(
                "INVALID_REQUEST",
                "consumer needs one packet placeholder",
            ));
        }
        if hash_file(&consumer.program)
            .map_err(|e| fail("CACHE_EXECUTION_FAILED", e))?
            .1
            != consumer.sha256
        {
            return Err(fail(
                "CACHE_EXECUTION_FAILED",
                "consumer executable identity",
            ));
        }
        let packet_path = entry.join("packet.bin");
        let args = consumer
            .args
            .iter()
            .map(|arg| {
                if arg == "{packet}" {
                    packet_path.to_string_lossy().into_owned()
                } else {
                    arg.clone()
                }
            })
            .collect::<Vec<_>>();
        let execute_started = Instant::now();
        let (stdout, stderr) = process(
            &consumer.program,
            &args,
            &request.working_directory,
            consumer.timeout_seconds,
        )
        .map_err(|e| fail("CACHE_EXECUTION_FAILED", e))?;
        timings.insert(
            "consumer_execution_seconds".into(),
            execute_started.elapsed().as_secs_f64(),
        );
        if hash_file(&consumer.program)
            .map_err(|e| fail("CACHE_EXECUTION_FAILED", e))?
            .1
            != consumer.sha256
        {
            return Err(fail(
                "CACHE_EXECUTION_FAILED",
                "consumer executable changed",
            ));
        }
        Some(json!({"stdout":stdout,"stderr":stderr,"executable_sha256":consumer.sha256}))
    } else {
        None
    };
    let final_started = Instant::now();
    if validate_entry(&entry, &request.identity, &key)
        .map_err(|e| fail("CACHE_INVALID_REJECTED", e))?
        != packet
    {
        return Err(fail(
            "CACHE_INVALID_REJECTED",
            "packet changed during consumption",
        ));
    }
    verify_sources(&request)?;
    timings.insert(
        "final_integrity_source_verification_seconds".into(),
        final_started.elapsed().as_secs_f64(),
    );
    timings.insert(
        "whole_cache_call_seconds".into(),
        started.elapsed().as_secs_f64(),
    );
    Ok(
        json!({"schema":"sof-runtime.prepared-input-cache-result.v1","status":status,"key":key,
              "packet_path":entry.join("packet.bin"),"packet":packet,"timings":timings,
              "invalid_reason":invalid_reason,"quarantine":quarantine,"consumer":consumer_result}),
    )
}

fn main() -> ExitCode {
    let result = (|| {
        let args = std::env::args().skip(1).collect::<Vec<_>>();
        if args.len() != 1 {
            return Err(fail(
                "INVALID_REQUEST",
                "usage: prepared-input-cache REQUEST.json",
            ));
        }
        let raw = fs::read(&args[0]).map_err(|e| fail("INVALID_REQUEST", e))?;
        if raw.len() > 1_000_000 {
            return Err(fail("INVALID_REQUEST", "request too large"));
        }
        let request =
            serde_json::from_slice::<Request>(&raw).map_err(|e| fail("INVALID_REQUEST", e))?;
        execute(request)
    })();
    match result {
        Ok(value) => {
            println!("{}", String::from_utf8(canonical(&value)).unwrap());
            ExitCode::SUCCESS
        }
        Err(error) => {
            println!(
                "{}",
                json!({"schema":"sof-runtime.prepared-input-cache-result.v1",
            "status":error.status,"detail":error.detail})
            );
            ExitCode::from(2)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn canonical_key_is_order_independent_but_content_sensitive() {
        let a: Value = serde_json::from_str(r#"{"b":2,"a":1}"#).unwrap();
        let b: Value = serde_json::from_str(r#"{"a":1,"b":2}"#).unwrap();
        assert_eq!(identity_key(&a), identity_key(&b));
        assert_ne!(identity_key(&a), identity_key(&json!({"a":1,"b":3})));
    }
}
