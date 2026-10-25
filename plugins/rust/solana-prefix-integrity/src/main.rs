use serde_json::{Value, json};
use std::time::Instant;

#[cfg(windows)]
mod counters {
    use std::ffi::c_void;
    #[repr(C)]
    #[derive(Default)]
    struct FileTime {
        low: u32,
        high: u32,
    }
    #[repr(C)]
    #[derive(Default)]
    struct Io {
        read_ops: u64,
        write_ops: u64,
        other_ops: u64,
        read_bytes: u64,
        write_bytes: u64,
        other_bytes: u64,
    }
    #[link(name = "kernel32")]
    unsafe extern "system" {
        fn GetCurrentProcess() -> *mut c_void;
        fn GetProcessTimes(
            process: *mut c_void,
            creation: *mut FileTime,
            exit: *mut FileTime,
            kernel: *mut FileTime,
            user: *mut FileTime,
        ) -> i32;
        fn GetProcessIoCounters(process: *mut c_void, io: *mut Io) -> i32;
    }
    pub fn sample() -> Result<[u64; 8], String> {
        let (mut creation, mut exit, mut kernel, mut user, mut io) = (
            FileTime::default(),
            FileTime::default(),
            FileTime::default(),
            FileTime::default(),
            Io::default(),
        );
        // The process pseudo-handle is valid for both documented queries.
        unsafe {
            let process = GetCurrentProcess();
            if GetProcessTimes(process, &mut creation, &mut exit, &mut kernel, &mut user) == 0
                || GetProcessIoCounters(process, &mut io) == 0
            {
                return Err("Windows process counters unavailable".into());
            }
        }
        Ok([
            ((user.high as u64) << 32) | user.low as u64,
            ((kernel.high as u64) << 32) | kernel.low as u64,
            io.read_ops,
            io.write_ops,
            io.other_ops,
            io.read_bytes,
            io.write_bytes,
            io.other_bytes,
        ])
    }
}
#[cfg(not(windows))]
mod counters {
    pub fn sample() -> Result<[u64; 8], String> {
        Err("this attribution contract requires Windows process counters".into())
    }
}
struct Meter {
    wall: Instant,
    before: [u64; 8],
}
impl Meter {
    fn start() -> Result<Self, String> {
        Ok(Self {
            before: counters::sample()?,
            wall: Instant::now(),
        })
    }
    fn finish(self, read: Option<u64>, written: u64) -> Result<Value, String> {
        let wall = self.wall.elapsed().as_secs_f64();
        let after = counters::sample()?;
        let mut delta = [0u64; 8];
        for i in 0..8 {
            delta[i] = after[i]
                .checked_sub(self.before[i])
                .ok_or("process counter moved backwards")?;
        }
        Ok(
            json!({"wall_seconds":wall,"user_cpu_seconds":delta[0] as f64/1e7,"kernel_cpu_seconds":delta[1] as f64/1e7,
            "cpu_seconds":(delta[0]+delta[1]) as f64/1e7,"logical_read_bytes":read,"logical_written_bytes":written,
            "os_process_io":{"read_operations":delta[2],"write_operations":delta[3],"other_operations":delta[4],
                "read_transfer_bytes":delta[5],"write_transfer_bytes":delta[6],"other_transfer_bytes":delta[7]}}),
        )
    }
}

#[allow(dead_code)]
mod frozen {
    include!("../../solana-incremental-replay/src/main.rs");

    pub fn probe(
        manifest: &Path,
        state: &Path,
        generator: &Path,
        anchor: &str,
        output: &Path,
        prefix: u64,
    ) -> Result<Value> {
        let total = crate::Meter::start()?;
        let mut phases = BTreeMap::new();
        let m = crate::Meter::start()?;
        let cap = Capture::load(manifest)?;
        phases.insert("metadata_admission", m.finish(None, 0)?);

        let m = crate::Meter::start()?;
        need(
            prefix > 0 && prefix <= cap.end - cap.start + 1,
            "prefix range",
        )?;
        need(
            !fs::symlink_metadata(state)
                .map_err(|e| e.to_string())?
                .file_type()
                .is_symlink(),
            "symlink state",
        )?;
        let root = state.canonicalize().map_err(|e| e.to_string())?;
        let parent = output
            .parent()
            .ok_or("aggregate parent")?
            .canonicalize()
            .map_err(|e| e.to_string())?;
        need(
            !parent.starts_with(&root) && !parent.starts_with(&cap.root),
            "aggregate output inside state/capture",
        )?;
        let lock_path = root.join("writer.lock");
        regular(&lock_path)?;
        let lock = OpenOptions::new()
            .read(true)
            .write(true)
            .open(lock_path)
            .map_err(|e| e.to_string())?;
        lock.try_lock_exclusive()
            .map_err(|_| "writer conflict".to_string())?;
        let (generator_hash, generator_bytes, _) = digest_file(generator)?;
        let identity = json!({"manifest_sha256":cap.sha,"projection":PROJECTION,"executable_sha256":generator_hash});
        let id_path = root.join("identity.json");
        let id_raw = small(&id_path, 65536)?;
        need(v0::strict(&id_raw)? == identity, "foreign state identity")?;
        let cp_path = root.join("checkpoint.json");
        let raw = small(&cp_path, 2 * 1024 * 1024)?;
        need(hash(&raw) == anchor, "external checkpoint anchor mismatch")?;
        let frame = v0::strict(&raw)?;
        let body = &frame["body"];
        need(
            frame["body_sha256"] == hash(&bytes(body))
                && body["schema"] == "sof-runtime.solana-checkpoint.v1"
                && body["identity"] == identity,
            "checkpoint frame/identity",
        )?;
        let entries = arr(&body["committed"])?;
        need(
            nat(&body["next_index"])? == prefix && entries.len() as u64 == prefix,
            "checkpoint cursor",
        )?;
        let mut allowed: BTreeSet<String> = ["writer.lock", "identity.json", "checkpoint.json"]
            .iter()
            .map(|s| s.to_string())
            .collect();
        allowed.extend(entries.iter().map(|e| format!("slot-{}.jsonl", e["slot"])));
        if prefix == cap.end - cap.start + 1 && root.join("projection.jsonl").exists() {
            allowed.insert("projection.jsonl".into());
        }
        let mut actual = BTreeSet::new();
        for e in fs::read_dir(&root).map_err(|e| e.to_string())? {
            let e = e.map_err(|e| e.to_string())?;
            regular(&e.path())?;
            actual.insert(e.file_name().to_string_lossy().to_string());
        }
        need(actual == allowed, "prefix state inventory")?;
        let mut previous = nat(&cap.m["anchor"]["slot"])?;
        let mut previous_hash = text(&cap.m["anchor"]["blockhash"])?.to_owned();
        for (i, entry) in entries.iter().enumerate() {
            need(
                nat(&entry["slot"])? == cap.start + i as u64,
                "checkpoint ordering",
            )?;
            continuity(&cap, entry, &mut previous, &mut previous_hash)?;
        }
        phases.insert(
            "checkpoint_anchor",
            m.finish(
                Some(generator_bytes + raw.len() as u64 + id_raw.len() as u64),
                0,
            )?,
        );

        let mut input_files = Vec::new();
        let mut segment_files = Vec::new();
        let mut input_bytes = 0;
        let m = crate::Meter::start()?;
        for entry in entries {
            let slot = nat(&entry["slot"])?;
            if let Some(item) = cap.item(slot) {
                let file_meter = crate::Meter::start()?;
                let path = v0::confined(&cap.root, text(&item["response"])?)?;
                let (digest, size, _) = digest_file(&path)?;
                need(
                    size <= 32 * 1024 * 1024 && digest == item["response_sha256"],
                    "prefix input byte identity mismatch",
                )?;
                input_bytes += size;
                input_files.push(json!({"slot":slot,"name":item["response"],"sha256":digest,"metrics":file_meter.finish(Some(size),0)?}));
            }
        }
        phases.insert("raw_input_hash", m.finish(Some(input_bytes), 0)?);

        let m = crate::Meter::start()?;
        let mut segment_bytes = 0;
        for entry in entries {
            let file_meter = crate::Meter::start()?;
            let slot = nat(&entry["slot"])?;
            let (digest, size, lines) = digest_file(&segment(&root, slot))?;
            need(
                digest == entry["sha256"]
                    && size == nat(&entry["bytes"])?
                    && lines == nat(&entry["records"])?,
                "committed segment corruption",
            )?;
            segment_bytes += size;
            segment_files.push(json!({"slot":slot,"name":format!("slot-{slot}.jsonl"),"sha256":digest,"metrics":file_meter.finish(Some(size),0)?}));
        }
        phases.insert("segment_validation", m.finish(Some(segment_bytes), 0)?);

        let m = crate::Meter::start()?;
        let mut out = OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(output)
            .map_err(|e| e.to_string())?;
        let mut buffer = [0u8; 65536];
        let mut digest = Sha256::new();
        let mut aggregate_bytes = 0;
        for entry in entries {
            let mut input =
                File::open(segment(&root, nat(&entry["slot"])?)).map_err(|e| e.to_string())?;
            let mut one = Sha256::new();
            let mut size = 0;
            loop {
                let n = input.read(&mut buffer).map_err(|e| e.to_string())?;
                if n == 0 {
                    break;
                }
                out.write_all(&buffer[..n]).map_err(|e| e.to_string())?;
                digest.update(&buffer[..n]);
                one.update(&buffer[..n]);
                size += n as u64;
            }
            need(
                format!("{:x}", one.finalize()) == entry["sha256"] && size == nat(&entry["bytes"])?,
                "segment changed during aggregation",
            )?;
            aggregate_bytes += size;
        }
        out.sync_all().map_err(|e| e.to_string())?;
        drop(out);
        let aggregate_hash = format!("{:x}", digest.finalize());
        let mut aggregate_read = aggregate_bytes;
        if root.join("projection.jsonl").exists() {
            let (digest, size, _) = digest_file(&root.join("projection.jsonl"))?;
            need(digest == aggregate_hash, "published aggregate corruption")?;
            aggregate_read += size;
        }
        phases.insert(
            "aggregate_stream",
            m.finish(Some(aggregate_read), aggregate_bytes)?,
        );

        let m = crate::Meter::start()?;
        let mut post_bytes = 0;
        for item in cap.m["rpc"].as_object().unwrap().values() {
            for (field, expected) in [
                ("request", "request_sha256"),
                ("response", "response_sha256"),
            ] {
                let (digest, size, _) =
                    digest_file(&v0::confined(&cap.root, text(&item[field])?)?)?;
                need(digest == item[expected], "input changed during consumption")?;
                post_bytes += size;
            }
        }
        for (path, expected) in [
            (manifest, cap.sha.as_str()),
            (
                cap.root.join("plan.json").as_path(),
                text(&cap.m["plan_sha256"])?,
            ),
            (cp_path.as_path(), anchor),
        ] {
            let (digest, size, _) = digest_file(path)?;
            need(digest == expected, "manifest/plan/checkpoint changed")?;
            post_bytes += size;
        }
        let last_id = small(&id_path, 65536)?;
        post_bytes += last_id.len() as u64;
        need(v0::strict(&last_id)? == identity, "state identity changed")?;
        phases.insert("post_consumption_integrity", m.finish(Some(post_bytes), 0)?);
        Ok(
            json!({"status":"MEASURED_VERIFIED_PREFIX","schema":"sof-runtime.prefix-integrity-probe.v1",
            "prefix_slots":prefix,"checkpoint_sha256":anchor,"checkpoint_identity":identity,
            "aggregate_sha256":aggregate_hash,"aggregate_bytes":aggregate_bytes,"block_decodes":0,"new_commits":0,
            "phases":phases,"raw_input_files":input_files,"segment_files":segment_files,
            "total":total.finish(None,aggregate_bytes)?}),
        )
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let result = (|| -> Result<Value, String> {
        if args.len() != 7 {
            return Err(
                "usage: MANIFEST STATE V1_BINARY CHECKPOINT_SHA AGGREGATE_OUTPUT PREFIX_SLOTS"
                    .into(),
            );
        }
        frozen::probe(
            std::path::Path::new(&args[1]),
            std::path::Path::new(&args[2]),
            std::path::Path::new(&args[3]),
            &args[4],
            std::path::Path::new(&args[5]),
            args[6].parse::<u64>().map_err(|e| e.to_string())?,
        )
    })();
    match result {
        Ok(value) => println!("{value}"),
        Err(error) => {
            println!("{}", json!({"status":"UNRESOLVED","error":error}));
            std::process::exit(2);
        }
    }
}
