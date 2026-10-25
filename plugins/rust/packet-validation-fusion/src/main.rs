use serde_json::{Value, json};
use std::process::ExitCode;

#[cfg(windows)]
fn cpu_seconds() -> Option<f64> {
    #[repr(C)]
    #[derive(Default)]
    struct FileTime {
        low: u32,
        high: u32,
    }
    #[link(name = "kernel32")]
    unsafe extern "system" {
        fn GetCurrentProcess() -> *mut std::ffi::c_void;
        fn GetProcessTimes(
            handle: *mut std::ffi::c_void,
            creation: *mut FileTime,
            exit: *mut FileTime,
            kernel: *mut FileTime,
            user: *mut FileTime,
        ) -> i32;
    }
    let (mut creation, mut exit, mut kernel, mut user) = (
        FileTime::default(),
        FileTime::default(),
        FileTime::default(),
        FileTime::default(),
    );
    // All pointers refer to live, correctly laid-out FILETIME storage.
    let ok = unsafe {
        GetProcessTimes(
            GetCurrentProcess(),
            &mut creation,
            &mut exit,
            &mut kernel,
            &mut user,
        )
    };
    if ok == 0 {
        return None;
    }
    let ticks = |value: FileTime| (u64::from(value.high) << 32) | u64::from(value.low);
    Some((ticks(kernel) + ticks(user)) as f64 / 10_000_000.0)
}

#[cfg(not(windows))]
fn cpu_seconds() -> Option<f64> {
    None
}

fn cpu_elapsed(start: Option<f64>) -> Option<f64> {
    Some(cpu_seconds()? - start?)
}

#[allow(dead_code)]
mod reference {
    include!(concat!(env!("OUT_DIR"), "/reference.rs"));
    use std::cell::{Cell, RefCell};

    #[derive(Default, Clone, Serialize)]
    struct IoCount {
        opens: u64,
        read_calls: u64,
        positive_reads: u64,
        bytes: u64,
    }

    thread_local! {
        static FUSED: Cell<bool> = const { Cell::new(false) };
        static IO: RefCell<BTreeMap<PathBuf, IoCount>> = const { RefCell::new(BTreeMap::new()) };
        static VALIDATIONS: RefCell<Vec<Value>> = const { RefCell::new(Vec::new()) };
    }

    struct TrackedFile {
        file: File,
        path: PathBuf,
    }

    fn tracked_open(path: &Path) -> std::io::Result<TrackedFile> {
        let file = File::open(path)?;
        IO.with_borrow_mut(|counts| counts.entry(path.to_owned()).or_default().opens += 1);
        Ok(TrackedFile {
            file,
            path: path.to_owned(),
        })
    }

    impl Read for TrackedFile {
        fn read(&mut self, buffer: &mut [u8]) -> std::io::Result<usize> {
            let result = self.file.read(buffer);
            IO.with_borrow_mut(|counts| {
                let count = counts.get_mut(&self.path).expect("registered open");
                count.read_calls += 1;
                if let Ok(length) = result {
                    count.bytes += length as u64;
                    count.positive_reads += u64::from(length > 0);
                }
            });
            result
        }
    }

    struct HashingReader<R> {
        inner: R,
        digest: Sha256,
        bytes: u64,
    }

    impl<R: Read> Read for HashingReader<R> {
        fn read(&mut self, buffer: &mut [u8]) -> std::io::Result<usize> {
            let length = self.inner.read(buffer)?;
            self.bytes = self
                .bytes
                .checked_add(length as u64)
                .ok_or_else(|| std::io::Error::other("packet length overflow"))?;
            self.digest.update(&buffer[..length]);
            Ok(length)
        }
    }

    struct ParsedPacket {
        header: Value,
        record_count: u64,
        edge_count: u64,
    }

    fn validate_packet_fused(path: &Path, identity: &Value) -> Outcome<Packet> {
        regular(path)?;
        let hashing = HashingReader {
            inner: tracked_open(path).map_err(|e| e.to_string())?,
            digest: Sha256::new(),
            bytes: 0,
        };
        let mut reader = BufReader::new(hashing);
        let parsed = parse_packet(&mut reader, identity)?;
        // parse_packet has required EOF, so no unparsed buffered tail is accepted.
        let hashing = reader.into_inner();
        Ok(Packet {
            name: "packet.bin".into(),
            size: hashing.bytes,
            sha256: format!("{:x}", hashing.digest.finalize()),
            header: parsed.header,
            record_count: parsed.record_count,
            edge_count: parsed.edge_count,
        })
    }

    fn validate_packet(path: &Path, identity: &Value) -> Outcome<Packet> {
        let started = Instant::now();
        let cpu = super::cpu_seconds();
        let result = if FUSED.get() {
            validate_packet_fused(path, identity)
        } else {
            validate_packet_reference(path, identity)
        };
        let cpu = super::cpu_elapsed(cpu);
        VALIDATIONS.with_borrow_mut(|values| {
            values.push(json!({"path":path,"accepted":result.is_ok(),
            "wall_seconds":started.elapsed().as_secs_f64(),"cpu_seconds":cpu}))
        });
        result
    }

    pub fn run(value: Value, mode: &str, action: &str) -> Value {
        FUSED.set(mode == "fused");
        let started = Instant::now();
        let cpu = super::cpu_seconds();
        let result = (|| -> Result<Value, Failure> {
            let request =
                serde_json::from_value::<Request>(value).map_err(|e| fail("INVALID_REQUEST", e))?;
            if action == "execute" {
                return execute(request);
            }
            valid_header(&request.identity["expected_header"])
                .map_err(|e| fail("INVALID_REQUEST", e))?;
            let key = identity_key(&request.identity);
            let packet = validate_entry(
                &request.cache_root.join("entries").join(key),
                &request.identity,
                &identity_key(&request.identity),
            )
            .map_err(|e| fail("CACHE_INVALID_REJECTED", e))?;
            Ok(json!({"status":"ENTRY_VALIDATED_NOT_CONSUMED","packet":packet}))
        })();
        let cpu = super::cpu_elapsed(cpu);
        let result = match result {
            Ok(value) => value,
            Err(error) => json!({"status":error.status,"detail":error.detail}),
        };
        json!({"schema":"sof-runtime.packet-validation-fusion.v1","mode":mode,"action":action,
            "result":result,"operation_wall_seconds":started.elapsed().as_secs_f64(),
            "operation_cpu_seconds_excludes_children":cpu,
            "validation_calls":VALIDATIONS.with_borrow(|values| values.clone()),
            "read_io":IO.with_borrow(|counts| counts.clone())})
    }

    #[cfg(test)]
    mod fusion_tests {
        use super::*;

        fn fixture_bytes(edge_count: u32) -> (Vec<u8>, Value) {
            let header = json!({"schema":"rime.malecns.profile-census-input.v1", "source_field":"test",
                "source_identity":"fixture", "sign_semantics":"test", "sector_labels":["A","B"],
                "record_count":1,"source_artifacts":[]});
            let encoded = canonical(&header);
            let mut bytes = b"RIMEPC01".to_vec();
            bytes.extend((encoded.len() as u32).to_le_bytes());
            bytes.extend(encoded);
            bytes.extend(0u64.to_le_bytes());
            bytes.extend(0u16.to_le_bytes());
            bytes.push(1);
            bytes.extend(edge_count.to_le_bytes());
            for index in 0..edge_count {
                bytes.extend((index as u16 % 2).to_le_bytes());
                bytes.extend(1u64.to_le_bytes());
            }
            (
                bytes,
                json!({"expected_header":header,"expected_edge_count":edge_count}),
            )
        }

        fn compare(path: &Path, bytes: &[u8], identity: &Value) -> bool {
            fs::write(path, bytes).unwrap();
            let reference = validate_packet_reference(path, identity);
            let fused = validate_packet_fused(path, identity);
            assert_eq!(reference.is_ok(), fused.is_ok());
            match (reference, fused) {
                (Ok(left), Ok(right)) => {
                    assert_eq!(left, right);
                    true
                }
                _ => false,
            }
        }

        #[test]
        fn all_small_prefixes_and_single_byte_mutations_agree() {
            let path = std::env::temp_dir().join(format!("packet-fusion-test-{}", token()));
            let (bytes, identity) = fixture_bytes(2);
            assert!(compare(&path, &bytes, &identity));
            for end in 0..bytes.len() {
                assert!(!compare(&path, &bytes[..end], &identity));
            }
            for index in 0..bytes.len() {
                let mut changed = bytes.clone();
                changed[index] ^= 1;
                compare(&path, &changed, &identity);
            }
            let mut trailing = bytes.clone();
            trailing.push(0);
            assert!(!compare(&path, &trailing, &identity));
            let mut wrong_count = identity.clone();
            wrong_count["expected_edge_count"] = json!(3);
            assert!(!compare(&path, &bytes, &wrong_count));
            fs::remove_file(path).unwrap();
        }

        #[test]
        fn digest_and_eof_agree_across_many_buffer_refills() {
            let path = std::env::temp_dir().join(format!("packet-fusion-test-{}", token()));
            let (bytes, identity) = fixture_bytes(10_000);
            assert!(bytes.len() > 8192);
            assert!(compare(&path, &bytes, &identity));
            assert!(!compare(&path, &bytes[..bytes.len() - 1], &identity));
            fs::remove_file(path).unwrap();
        }

        #[test]
        fn hashing_reader_handles_short_reads_and_empty_input() {
            for input in [b"".as_slice(), b"abcdef".as_slice()] {
                let mut hashing = HashingReader {
                    inner: std::io::Cursor::new(input),
                    digest: Sha256::new(),
                    bytes: 0,
                };
                let mut buffer = [0u8; 2];
                while hashing.read(&mut buffer).unwrap() != 0 {}
                assert_eq!(hashing.bytes, input.len() as u64);
                assert_eq!(
                    format!("{:x}", hashing.digest.finalize()),
                    format!("{:x}", Sha256::digest(input))
                );
            }
        }
    }
}

fn run() -> Result<Value, String> {
    let args = std::env::args().skip(1).collect::<Vec<_>>();
    if args.len() != 3
        || !matches!(args[0].as_str(), "reference" | "fused")
        || !matches!(args[1].as_str(), "execute" | "validate")
    {
        return Err(
            "usage: packet-validation-fusion reference|fused execute|validate REQUEST.json".into(),
        );
    }
    let raw = std::fs::read(&args[2]).map_err(|e| e.to_string())?;
    if raw.len() > 1_000_000 {
        return Err("request too large".into());
    }
    let request = serde_json::from_slice(&raw).map_err(|e| e.to_string())?;
    Ok(reference::run(request, &args[0], &args[1]))
}

fn main() -> ExitCode {
    let result = match run() {
        Ok(value) => value,
        Err(detail) => json!({"result":{"status":"INVALID_REQUEST","detail":detail}}),
    };
    let success = matches!(
        result["result"]["status"].as_str(),
        Some(
            "CACHE_MISS_PREPARED"
                | "CACHE_HIT_VALIDATED"
                | "CACHE_INVALID_REBUILT"
                | "ENTRY_VALIDATED_NOT_CONSUMED"
        )
    );
    println!("{result}");
    if success {
        ExitCode::SUCCESS
    } else {
        ExitCode::from(2)
    }
}
