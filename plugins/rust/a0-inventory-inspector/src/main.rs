use a0_inventory_inspector::{Error, Result, identity::ContentDigest};
use serde_json::json;
use sha2::{Digest, Sha256};
use std::io::{Read, Write};
use std::path::Path;
use std::time::{Instant, SystemTime, UNIX_EPOCH};

fn now() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_millis() as u64
}
fn main() {
    let a: Vec<String> = std::env::args().collect();
    if a.len() != 4 && !(a.len() == 7 && a[4] == "--pause") {
        println!("{}", json!({"status":"INCOMPLETE","code":"USAGE"}));
        std::process::exit(3);
    }
    let started = now();
    let clock = Instant::now();
    let inspected = (|| -> Result<(serde_json::Value, ContentDigest)> {
        let (root, manifest, bindings) = (Path::new(&a[1]), Path::new(&a[2]), Path::new(&a[3]));
        if a.len() == 7 {
            a0_inventory_inspector::check_marker(Path::new(&a[6]), root, manifest, bindings)?;
        }
        let mut hasher = Sha256::new();
        let mut executable = std::fs::File::open(
            std::env::current_exe()
                .map_err(|e| Error::unresolved("OBSERVER_IDENTITY", e.to_string()))?,
        )
        .map_err(|e| Error::unresolved("OBSERVER_IDENTITY", e.to_string()))?;
        let mut buf = [0; 65536];
        loop {
            let n = executable
                .read(&mut buf)
                .map_err(|e| Error::unresolved("OBSERVER_IDENTITY", e.to_string()))?;
            if n == 0 {
                break;
            }
            hasher.update(&buf[..n]);
        }
        let identity = ContentDigest::from_hasher(hasher);
        let mut hook = |point: &str| -> Result<()> {
            if a.len() == 7 && point == a[5] {
                // Test-only marker; no library write or publication primitive.
                let mut f = std::fs::OpenOptions::new()
                    .create_new(true)
                    .write(true)
                    .open(&a[6])
                    .map_err(|e| Error::unresolved("FAULT_MARKER", e.to_string()))?;
                f.write_all(
                    &serde_json::to_vec(&json!({"point":point,"pid":std::process::id()})).unwrap(),
                )
                .and_then(|_| f.sync_all())
                .map_err(|e| Error::unresolved("FAULT_MARKER", e.to_string()))?;
                drop(f);
                loop {
                    let release = format!("{}.continue", a[6]);
                    if Path::new(&release).exists() {
                        if std::fs::read(release)
                            .map_err(|e| Error::unresolved("FAULT_MARKER", e.to_string()))?
                            != b"continue"
                        {
                            return Err(Error::unresolved("FAULT_MARKER", "invalid test release"));
                        }
                        break;
                    }
                    std::thread::sleep(std::time::Duration::from_millis(50));
                }
            }
            Ok(())
        };
        let result = a0_inventory_inspector::inspect(root, manifest, bindings, &mut hook)?;
        Ok((result, identity))
    })();
    let ended = now();
    let (value, code) = match inspected {
        Ok((inspection, identity)) => (
            json!({"schema":"sof-runtime.a0-inspection-result.v0","status":"INTEGRITY_MATCHES",
            "observer_identity":{"role":"ShadowObserverExecution","sha256":identity},"inspection":inspection,
            "window":{"started_unix_ms":started,"ended_unix_ms":ended,"elapsed_ns":clock.elapsed().as_nanos() as u64},
            "validity":"OBSERVED_INTERVAL_ONLY","source_trust":"NOT_ASSESSED","application_decision":"NOT_ASSESSED"}),
            0,
        ),
        Err(e) => (
            json!({"schema":"sof-runtime.a0-inspection-result.v0","status":e.class,"error":e,
            "window":{"started_unix_ms":started,"ended_unix_ms":ended},"source_trust":"NOT_ASSESSED","application_decision":"NOT_ASSESSED"}),
            3,
        ),
    };
    let bytes = serde_json::to_vec(&value).unwrap();
    let mut stdout = std::io::stdout().lock();
    if a.len() == 7 && a[5] == "result_partial" && code == 0 {
        let split = bytes.len() / 2;
        stdout.write_all(&bytes[..split]).unwrap();
        stdout.flush().unwrap();
        let mut f = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&a[6])
            .unwrap();
        f.write_all(
            &serde_json::to_vec(&json!({"point":"result_partial","pid":std::process::id()}))
                .unwrap(),
        )
        .unwrap();
        f.sync_all().unwrap();
        drop(f);
        loop {
            std::thread::sleep(std::time::Duration::from_millis(50));
        }
    }
    stdout.write_all(&bytes).unwrap();
    stdout.flush().unwrap();
    drop(stdout);
    if code != 0 {
        std::process::exit(code);
    }
}
