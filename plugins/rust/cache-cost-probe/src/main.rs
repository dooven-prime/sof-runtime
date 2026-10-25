use serde::Deserialize;
use serde_json::{Value, json};
use std::io::{self, BufRead, Read, Write};
use std::process::ExitCode;
use std::time::Instant;

// Import the byte-bound baseline without editing or reimplementing its checks.
#[allow(dead_code)]
mod reference {
    include!("../../prepared-input-cache/src/main.rs");

    pub fn run(value: Value, action: &str) -> Value {
        let request = match serde_json::from_value::<Request>(value) {
            Ok(request) => request,
            Err(error) => return json!({"status":"INVALID_REQUEST","detail":error.to_string()}),
        };
        if action == "execute" {
            return match execute(request) {
                Ok(result) => result,
                Err(error) => json!({"status":error.status,"detail":error.detail}),
            };
        }
        let result = (|| -> Outcome<Value> {
            let started = Instant::now();
            verify_sources(&request).map_err(|e| format!("{}: {}", e.status, e.detail))?;
            let source_seconds = started.elapsed().as_secs_f64();
            let key = identity_key(&request.identity);
            let entry = request.cache_root.join("entries").join(&key);
            let started = Instant::now();
            let (size, digest) = hash_file(&entry.join("packet.bin"))?;
            let hash_seconds = started.elapsed().as_secs_f64();
            let started = Instant::now();
            let packet = validate_entry(&entry, &request.identity, &key)?;
            let validation_seconds = started.elapsed().as_secs_f64();
            if packet.size != size || packet.sha256 != digest {
                return Err("packet changed between isolated probes".into());
            }
            Ok(
                json!({"status":"PROBED_NOT_CONSUMED","key":key,"packet":packet,
                "source_preparer_seconds":source_seconds,"packet_hash_only_seconds":hash_seconds,
                "packet_full_entry_validation_seconds":validation_seconds}),
            )
        })();
        match result {
            Ok(result) => result,
            Err(detail) => json!({"status":"PROBE_REJECTED","detail":detail}),
        }
    }
}

const SCHEMA: &str = "sof-runtime.cache-cost-probe.v1";
const MAX_BYTES: u64 = 1_000_000;
const MAX_REQUESTS: u64 = 64;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Envelope {
    schema: String,
    id: u64,
    action: String,
    request: Option<Value>,
}

fn handle(raw: &[u8], expected_id: u64) -> Result<Value, String> {
    if raw.len() as u64 > MAX_BYTES {
        return Err("request exceeds 1 MB".into());
    }
    let envelope: Envelope = serde_json::from_slice(raw).map_err(|e| e.to_string())?;
    if envelope.schema != SCHEMA || envelope.id != expected_id {
        return Err("schema or sequential id mismatch".into());
    }
    let started = Instant::now();
    let result = match envelope.action.as_str() {
        "ping" if envelope.request.is_none() => json!({"status":"PONG"}),
        "execute" | "probe" => reference::run(
            envelope.request.ok_or("missing cache request")?,
            &envelope.action,
        ),
        _ => return Err("unknown action or ping payload".into()),
    };
    Ok(json!({"schema":SCHEMA,"id":expected_id,"result":result,
        "dispatch_seconds":started.elapsed().as_secs_f64()}))
}

fn emit(value: Value) -> Result<(), String> {
    let mut output = io::stdout().lock();
    serde_json::to_writer(&mut output, &value).map_err(|e| e.to_string())?;
    output.write_all(b"\n").map_err(|e| e.to_string())?;
    output.flush().map_err(|e| e.to_string())
}

fn run() -> Result<(), String> {
    let args = std::env::args().skip(1).collect::<Vec<_>>();
    if args.len() == 2 && args[0] == "--once" {
        let file = std::fs::File::open(&args[1]).map_err(|e| e.to_string())?;
        let mut raw = Vec::new();
        std::io::Read::take(file, MAX_BYTES + 1)
            .read_to_end(&mut raw)
            .map_err(|e| e.to_string())?;
        return emit(handle(&raw, 0)?);
    }
    if !args.is_empty() {
        return Err("usage: cache-cost-probe [--once ENVELOPE.json]".into());
    }
    emit(
        json!({"schema":SCHEMA,"status":"READY","pid":std::process::id(),
        "max_requests":MAX_REQUESTS,"retained_validation_credentials":false}),
    )?;
    let mut input = io::stdin().lock();
    for id in 0..MAX_REQUESTS {
        let mut raw = Vec::new();
        let count = std::io::Read::take(&mut input, MAX_BYTES + 1)
            .read_until(b'\n', &mut raw)
            .map_err(|e| e.to_string())?;
        if count == 0 {
            return Ok(());
        }
        if !raw.ends_with(b"\n") {
            return Err("unterminated or oversized JSONL frame".into());
        }
        emit(handle(&raw, id)?)?;
    }
    Ok(())
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(detail) => {
            let _ = emit(json!({"schema":SCHEMA,"status":"PROTOCOL_REJECTED","detail":detail}));
            ExitCode::from(2)
        }
    }
}
