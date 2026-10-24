use fs2::FileExt;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;

// Compile the frozen projection implementation without changing its source.
#[allow(dead_code)]
mod v0 {
    include!("../../solana-offchain-slice/src/main.rs");
    pub fn strict(raw: &[u8]) -> Result<Value> {
        parse(raw)
    }
    pub fn project(slot: u64, block: &Value) -> Result<Vec<Value>> {
        project_block(slot, block)
    }
    pub fn response(root: &Path, item: &Value) -> Result<Value> {
        rpc(root, item)
    }
    pub fn cfg() -> Value {
        config()
    }
    pub fn confined(root: &Path, name: &str) -> Result<PathBuf> {
        local(root, name)
    }
    pub fn key(v: &Value) -> Result<String> {
        b58(v, Some(32))
    }
}
type Result<T> = std::result::Result<T, String>;
const PROJECTION: &str = "sof-runtime.solana-projection.v0";
fn need(ok: bool, message: &str) -> Result<()> {
    if ok { Ok(()) } else { Err(message.into()) }
}
fn nat(v: &Value) -> Result<u64> {
    v.as_u64().ok_or("expected unsigned integer".into())
}
fn text(v: &Value) -> Result<&str> {
    v.as_str().ok_or("expected string".into())
}
fn arr(v: &Value) -> Result<&Vec<Value>> {
    v.as_array().ok_or("expected array".into())
}
fn bytes(v: &Value) -> Vec<u8> {
    serde_json::to_vec(v).unwrap()
}
fn hash(b: &[u8]) -> String {
    format!("{:x}", Sha256::digest(b))
}
fn regular(path: &Path) -> Result<()> {
    let m = fs::symlink_metadata(path).map_err(|e| e.to_string())?;
    need(
        m.is_file() && !m.file_type().is_symlink(),
        "not a regular file",
    )
}
fn small(path: &Path, limit: u64) -> Result<Vec<u8>> {
    regular(path)?;
    need(
        fs::metadata(path).map_err(|e| e.to_string())?.len() <= limit,
        "file byte limit",
    )?;
    fs::read(path).map_err(|e| e.to_string())
}
fn digest_file(path: &Path) -> Result<(String, u64, u64)> {
    regular(path)?;
    let mut file = File::open(path).map_err(|e| e.to_string())?;
    let mut digest = Sha256::new();
    let mut buffer = [0u8; 65536];
    let (mut size, mut lines) = (0, 0);
    loop {
        let n = file.read(&mut buffer).map_err(|e| e.to_string())?;
        if n == 0 {
            break;
        }
        digest.update(&buffer[..n]);
        size += n as u64;
        lines += buffer[..n].iter().filter(|b| **b == b'\n').count() as u64;
    }
    Ok((format!("{:x}", digest.finalize()), size, lines))
}

struct Capture {
    root: PathBuf,
    m: Value,
    sha: String,
    start: u64,
    end: u64,
    blocks: BTreeMap<u64, Value>,
}
impl Capture {
    fn load(path: &Path) -> Result<Self> {
        let raw = small(path, 1024 * 1024)?;
        let m = v0::strict(&raw)?;
        let root = path
            .parent()
            .ok_or("manifest parent")?
            .canonicalize()
            .map_err(|e| e.to_string())?;
        need(
            m["schema"] == "sof-runtime.solana-capture.v1"
                && m["projection"] == PROJECTION
                && m["config"] == v0::cfg()
                && m["commitment"] == "finalized",
            "capture contract",
        )?;
        need(
            (m["capture_kind"] == "rpc_capture" || m["capture_kind"] == "synthetic_control")
                && m["finality_independently_verified"] == false,
            "capture provenance boundary",
        )?;
        let (start, end) = (nat(&m["start_slot"])?, nat(&m["end_slot"])?);
        need(
            end >= start && end - start < 256 && end < u64::MAX,
            "range limit",
        )?;
        let plan = v0::confined(&root, "plan.json")?;
        need(
            digest_file(&plan)?.0 == text(&m["plan_sha256"])?,
            "capture plan identity",
        )?;
        let mut blocks = BTreeMap::new();
        let mut previous = None;
        for b in arr(&m["listed_blocks"])? {
            let slot = nat(&b["slot"])?;
            need(
                start <= slot && slot <= end && previous.is_none_or(|p| p < slot),
                "listed slot order",
            )?;
            need(b["role"] == format!("block-{slot}"), "block role")?;
            v0::key(&b["blockhash"])?;
            blocks.insert(slot, b.clone());
            previous = Some(slot);
        }
        need(!blocks.is_empty(), "empty listed blocks")?;
        let required: BTreeSet<String> = [
            "version",
            "genesis",
            "genesis_after",
            "root_before",
            "root_after",
            "index_before",
            "index_after",
            "anchor",
        ]
        .iter()
        .map(|s| s.to_string())
        .chain(blocks.keys().map(|s| format!("block-{s}")))
        .collect();
        let rpc = m["rpc"].as_object().ok_or("RPC inventory")?;
        need(
            rpc.keys().cloned().collect::<BTreeSet<_>>() == required,
            "RPC role inventory",
        )?;
        let slots: Vec<u64> = blocks.keys().copied().collect();
        let mut ids = BTreeSet::new();
        let mut filenames = BTreeSet::new();
        for (role, item) in rpc {
            need(ids.insert(nat(&item["id"])?), "duplicate RPC id")?;
            for field in ["request", "response"] {
                need(
                    filenames.insert(text(&item[field])?.to_string()),
                    "aliased RPC file",
                )?;
                v0::confined(&root, text(&item[field])?)?;
            }
            let request_raw = small(&v0::confined(&root, text(&item["request"])?)?, 65536)?;
            need(
                hash(&request_raw) == item["request_sha256"],
                "request byte identity",
            )?;
            let request = v0::strict(&request_raw)?;
            need(
                request
                    == json!({"jsonrpc":"2.0","id":item["id"],"method":item["method"],"params":item["params"]}),
                "request envelope",
            )?;
            let (method, params) = if let Some(slot) = role.strip_prefix("block-") {
                (
                    "getBlock",
                    json!([slot.parse::<u64>().map_err(|e| e.to_string())?, v0::cfg()]),
                )
            } else {
                match role.as_str() {
                    "version" => ("getVersion", json!([])),
                    "genesis" | "genesis_after" => ("getGenesisHash", json!([])),
                    "root_before" | "root_after" => {
                        ("getSlot", json!([{"commitment":"finalized"}]))
                    }
                    "index_before" | "index_after" => {
                        ("getBlocks", json!([start,end,{"commitment":"finalized"}]))
                    }
                    "anchor" => {
                        let mut c = v0::cfg();
                        c["transactionDetails"] = json!("none");
                        ("getBlock", json!([nat(&m["anchor"]["slot"])?, c]))
                    }
                    _ => return Err("unknown role".into()),
                }
            };
            need(
                item["method"] == method && item["params"] == params,
                "RPC method/config",
            )?;
            if role.starts_with("block-") {
                continue;
            }
            let value = v0::response(&root, item)?;
            match role.as_str() {
                "version" => need(
                    value == m["server_version"] && value["solana-core"].is_string(),
                    "version metadata",
                )?,
                "genesis" | "genesis_after" => {
                    need(value == v0::key(&m["genesis"])?, "cluster mismatch")?
                }
                "root_before" | "root_after" => need(nat(&value)? >= end, "root below capture")?,
                "index_before" | "index_after" => {
                    need(value == json!(slots), "source index mismatch")?
                }
                "anchor" => need(
                    value["blockhash"] == v0::key(&m["anchor"]["blockhash"])?,
                    "anchor mismatch",
                )?,
                _ => {}
            }
        }
        Ok(Self {
            root,
            m,
            sha: hash(&raw),
            start,
            end,
            blocks,
        })
    }
    fn item(&self, slot: u64) -> Option<&Value> {
        self.blocks
            .get(&slot)
            .map(|_| &self.m["rpc"][format!("block-{slot}")])
    }
    fn source_hash(&self, slot: u64) -> Value {
        self.item(slot)
            .map_or(Value::Null, |item| item["response_sha256"].clone())
    }
    fn verify_input(&self, slot: u64) -> Result<u64> {
        if let Some(item) = self.item(slot) {
            let (digest, size, _) =
                digest_file(&v0::confined(&self.root, text(&item["response"])?)?)?;
            need(
                size <= 32 * 1024 * 1024 && digest == item["response_sha256"],
                "prefix input byte identity mismatch",
            )?;
            Ok(size)
        } else {
            Ok(0)
        }
    }
}

#[derive(Default)]
struct Work {
    prefix_slots: Vec<u64>,
    suffix_slots: Vec<u64>,
    prefix_decode_bytes: u64,
    suffix_decode_bytes: u64,
    prefix_input_bytes: u64,
    prefix_segment_bytes: u64,
    post_input_bytes: u64,
    aggregate_bytes: u64,
    newly_committed_slots: u64,
    adopted_orphans: u64,
    timings: BTreeMap<String, f64>,
}
impl Work {
    fn time(&mut self, key: &str, start: Instant) {
        *self.timings.entry(key.into()).or_default() += start.elapsed().as_secs_f64();
    }
    fn value(&self) -> Value {
        json!({"prefix_decoded_slots":self.prefix_slots,"suffix_decoded_slots":self.suffix_slots,
        "prefix_decode_bytes":self.prefix_decode_bytes,"suffix_decode_bytes":self.suffix_decode_bytes,
        "prefix_verified_input_bytes":self.prefix_input_bytes,"prefix_verified_segment_bytes":self.prefix_segment_bytes,
        "post_verified_input_bytes":self.post_input_bytes,"aggregate_bytes":self.aggregate_bytes,
        "newly_committed_slots":self.newly_committed_slots,"adopted_orphans":self.adopted_orphans,"phase_seconds":self.timings})
    }
}
fn project(
    cap: &Capture,
    slot: u64,
    prefix: bool,
    forbid_prefix: bool,
    work: &mut Work,
) -> Result<(Vec<u8>, Value)> {
    need(!prefix || !forbid_prefix, "committed-prefix decode trap")?;
    let records = if let Some(item) = cap.item(slot) {
        let size = fs::metadata(v0::confined(&cap.root, text(&item["response"])?)?)
            .map_err(|e| e.to_string())?
            .len();
        need(size <= 32 * 1024 * 1024, "block response byte limit")?;
        if prefix {
            work.prefix_slots.push(slot);
            work.prefix_decode_bytes += size;
        } else {
            work.suffix_slots.push(slot);
            work.suffix_decode_bytes += size;
        }
        v0::project(slot, &v0::response(&cap.root, item)?)?
    } else {
        vec![json!({"kind":"not_listed_by_source","slot":slot})]
    };
    let mut raw = Vec::new();
    for r in &records {
        raw.extend(bytes(r));
        raw.push(b'\n');
    }
    let entry = json!({"slot":slot,"sha256":hash(&raw),"bytes":raw.len(),"records":records.len(),
        "input_sha256":cap.source_hash(slot),"header":records[0]});
    Ok((raw, entry))
}
fn continuity(
    cap: &Capture,
    entry: &Value,
    previous: &mut u64,
    previous_hash: &mut String,
) -> Result<()> {
    let slot = nat(&entry["slot"])?;
    let header = &entry["header"];
    need(
        nat(&header["slot"])? == slot && entry["input_sha256"] == cap.source_hash(slot),
        "checkpoint source/slot mismatch",
    )?;
    if let Some(b) = cap.blocks.get(&slot) {
        need(
            header["kind"] == "block"
                && header["blockhash"] == b["blockhash"]
                && nat(&header["parent_slot"])? == *previous
                && header["previous_blockhash"] == *previous_hash
                && nat(&entry["records"])?
                    == nat(&header["transaction_count"])?
                        .checked_add(1)
                        .ok_or("record overflow")?,
            "checkpoint chain/records mismatch",
        )?;
        *previous = slot;
        *previous_hash = text(&header["blockhash"])?.to_owned();
    } else {
        need(
            header == &json!({"kind":"not_listed_by_source","slot":slot})
                && nat(&entry["records"])? == 1,
            "unlisted marker mismatch",
        )?;
    }
    Ok(())
}
struct Fault {
    point: String,
    slot: u64,
}
fn pause(fault: &Option<Fault>, point: &str, slot: u64) {
    if fault
        .as_ref()
        .is_some_and(|f| f.point == point && f.slot == slot)
    {
        println!(
            "{}",
            json!({"status":"FAULT_REACHED","point":point,"slot":slot})
        );
        std::io::stdout().flush().unwrap();
        loop {
            std::thread::sleep(std::time::Duration::from_secs(1));
        }
    }
}
fn publish(
    path: &Path,
    raw: &[u8],
    fault: &Option<Fault>,
    partial: &str,
    complete: &str,
    slot: u64,
) -> Result<()> {
    let temp = path.with_extension("tmp");
    if temp.exists() {
        regular(&temp)?;
        fs::remove_file(&temp).map_err(|e| e.to_string())?;
    }
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&temp)
        .map_err(|e| e.to_string())?;
    let half = raw.len() / 2;
    file.write_all(&raw[..half])
        .and_then(|_| file.sync_all())
        .map_err(|e| e.to_string())?;
    pause(fault, partial, slot);
    file.write_all(&raw[half..])
        .and_then(|_| file.sync_all())
        .map_err(|e| e.to_string())?;
    drop(file);
    fs::rename(&temp, path).map_err(|e| e.to_string())?;
    pause(fault, complete, slot);
    Ok(())
}
fn checkpoint(identity: &Value, entries: &[Value]) -> Vec<u8> {
    let body = json!({"schema":"sof-runtime.solana-checkpoint.v1","identity":identity,"next_index":entries.len(),"committed":entries});
    bytes(&json!({"body_sha256":hash(&bytes(&body)),"body":body}))
}
fn segment(root: &Path, slot: u64) -> PathBuf {
    root.join(format!("slot-{slot}.jsonl"))
}

fn execute(
    manifest: &Path,
    output: &Path,
    mode: &str,
    anchor: Option<&str>,
    fault: Option<Fault>,
    forbid_prefix: bool,
) -> Result<Value> {
    let mut work = Work::default();
    let time = Instant::now();
    let cap = Capture::load(manifest)?;
    let identity = json!({"manifest_sha256":cap.sha,"projection":PROJECTION,
        "executable_sha256":digest_file(&std::env::current_exe().map_err(|e| e.to_string())?)?.0});
    work.time("metadata_validation", time);
    if !output.exists() {
        fs::create_dir_all(output).map_err(|e| e.to_string())?;
    }
    need(
        !fs::symlink_metadata(output)
            .map_err(|e| e.to_string())?
            .file_type()
            .is_symlink(),
        "symlink state directory",
    )?;
    let root = output.canonicalize().map_err(|e| e.to_string())?;
    need(root != cap.root, "state cannot be capture directory")?;
    let lock_path = root.join("writer.lock");
    if lock_path.exists() {
        regular(&lock_path)?;
    }
    let lock = OpenOptions::new()
        .create(true)
        .truncate(false)
        .read(true)
        .write(true)
        .open(&lock_path)
        .map_err(|e| e.to_string())?;
    lock.try_lock_exclusive()
        .map_err(|_| "writer conflict".to_string())?;
    let mut allowed: BTreeSet<String> = [
        "writer.lock",
        "identity.json",
        "identity.tmp",
        "checkpoint.json",
        "checkpoint.tmp",
        "projection.jsonl",
        "projection.tmp",
    ]
    .iter()
    .map(|s| s.to_string())
    .collect();
    for s in cap.start..=cap.end {
        allowed.insert(format!("slot-{s}.jsonl"));
        allowed.insert(format!("slot-{s}.tmp"));
    }
    for e in fs::read_dir(&root).map_err(|e| e.to_string())? {
        let e = e.map_err(|e| e.to_string())?;
        need(
            allowed.contains(&e.file_name().to_string_lossy().to_string()),
            "unknown state artifact",
        )?;
        regular(&e.path())?;
    }
    let id_path = root.join("identity.json");
    let cp_path = root.join("checkpoint.json");
    if id_path.exists() {
        need(
            v0::strict(&small(&id_path, 65536)?)? == identity,
            "foreign state identity",
        )?;
    } else {
        need(
            !cp_path.exists()
                && !(cap.start..=cap.end).any(|s| segment(&root, s).exists())
                && !root.join("projection.jsonl").exists(),
            "state without identity",
        )?;
        publish(&id_path, &bytes(&identity), &None, "", "", cap.start)?;
    }
    let mut entries: Vec<Value> = Vec::new();
    if cp_path.exists() {
        let raw = small(&cp_path, 2 * 1024 * 1024)?;
        let frame = v0::strict(&raw)?;
        let body = &frame["body"];
        need(
            frame["body_sha256"] == hash(&bytes(body))
                && body["schema"] == "sof-runtime.solana-checkpoint.v1"
                && body["identity"] == identity,
            "checkpoint frame/identity",
        )?;
        entries = arr(&body["committed"])?.clone();
        need(
            nat(&body["next_index"])? == entries.len() as u64
                && entries.len() as u64 <= cap.end - cap.start + 1,
            "checkpoint cursor",
        )?;
        if let Some(expected) = anchor {
            need(
                hash(&raw) == expected,
                "external checkpoint anchor mismatch",
            )?;
        }
        if !entries.is_empty() && mode == "incremental" {
            need(
                anchor.is_some(),
                "nonempty incremental prefix requires prior checkpoint anchor",
            )?;
        }
    } else {
        need(anchor.is_none(), "anchor supplied without checkpoint")?;
        publish(
            &cp_path,
            &checkpoint(&identity, &entries),
            &None,
            "",
            "",
            cap.start,
        )?;
    }
    let initial = entries.len();
    let next_slot = cap.start + initial as u64;
    for slot in next_slot..=cap.end {
        if segment(&root, slot).exists() {
            need(slot == next_slot, "noncontiguous orphan")?;
        }
    }
    for e in fs::read_dir(&root).map_err(|e| e.to_string())? {
        let path = e.map_err(|e| e.to_string())?.path();
        if path.extension().is_some_and(|s| s == "tmp") {
            fs::remove_file(path).map_err(|e| e.to_string())?;
        }
    }
    let mut previous = nat(&cap.m["anchor"]["slot"])?;
    let mut previous_hash = text(&cap.m["anchor"]["blockhash"])?.to_owned();
    let time = Instant::now();
    for (i, entry) in entries.iter().enumerate() {
        let slot = cap.start + i as u64;
        need(nat(&entry["slot"])? == slot, "checkpoint ordering")?;
        continuity(&cap, entry, &mut previous, &mut previous_hash)?;
        work.prefix_input_bytes += cap.verify_input(slot)?;
        let (digest, size, lines) = digest_file(&segment(&root, slot))?;
        need(
            digest == entry["sha256"]
                && size == nat(&entry["bytes"])?
                && lines == nat(&entry["records"])?,
            "committed segment corruption",
        )?;
        work.prefix_segment_bytes += size;
    }
    work.time("prefix_integrity", time);
    if mode == "full_reproject" {
        let time = Instant::now();
        for entry in &entries {
            let (_, expected) =
                project(&cap, nat(&entry["slot"])?, true, forbid_prefix, &mut work)?;
            need(&expected == entry, "full-reproject prefix mismatch")?;
        }
        work.time("prefix_reprojection", time);
    }
    for slot in next_slot..=cap.end {
        let time = Instant::now();
        let (raw, entry) = project(&cap, slot, false, forbid_prefix, &mut work)?;
        continuity(&cap, &entry, &mut previous, &mut previous_hash)?;
        work.time("suffix_decode_project", time);
        let time = Instant::now();
        let path = segment(&root, slot);
        if path.exists() {
            need(
                digest_file(&path)?.0 == hash(&raw),
                "uncommitted orphan mismatch",
            )?;
            work.adopted_orphans += 1;
        } else {
            publish(
                &path,
                &raw,
                &fault,
                "partial_segment",
                "segment_publish",
                slot,
            )?;
        }
        entries.push(entry);
        publish(
            &cp_path,
            &checkpoint(&identity, &entries),
            &fault,
            "partial_checkpoint",
            "checkpoint_publish",
            slot,
        )?;
        work.newly_committed_slots += 1;
        work.time("new_commit", time);
    }
    let time = Instant::now();
    let temporary = root.join("projection.tmp");
    let mut aggregate = OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(&temporary)
        .map_err(|e| e.to_string())?;
    let mut digest = Sha256::new();
    let mut record_count = 0;
    let mut buffer = [0u8; 65536];
    for entry in &entries {
        let mut input =
            File::open(segment(&root, nat(&entry["slot"])?)).map_err(|e| e.to_string())?;
        let mut segment_digest = Sha256::new();
        loop {
            let n = input.read(&mut buffer).map_err(|e| e.to_string())?;
            if n == 0 {
                break;
            }
            aggregate
                .write_all(&buffer[..n])
                .map_err(|e| e.to_string())?;
            digest.update(&buffer[..n]);
            segment_digest.update(&buffer[..n]);
            work.aggregate_bytes += n as u64;
            if work.aggregate_bytes == n as u64 {
                aggregate.sync_all().map_err(|e| e.to_string())?;
                pause(&fault, "partial_projection", cap.end);
            }
        }
        need(
            format!("{:x}", segment_digest.finalize()) == entry["sha256"],
            "segment changed during aggregation",
        )?;
        record_count += nat(&entry["records"])?;
    }
    aggregate.sync_all().map_err(|e| e.to_string())?;
    drop(aggregate);
    let output_hash = format!("{:x}", digest.finalize());
    let projection = root.join("projection.jsonl");
    if projection.exists() {
        need(
            digest_file(&projection)?.0 == output_hash,
            "published aggregate corruption",
        )?;
        fs::remove_file(&temporary).map_err(|e| e.to_string())?;
    } else {
        fs::rename(&temporary, &projection).map_err(|e| e.to_string())?;
    }
    pause(&fault, "projection_publish", cap.end);
    work.time("aggregation", time);
    let time = Instant::now();
    for item in cap.m["rpc"].as_object().unwrap().values() {
        for (field, expected) in [
            ("request", "request_sha256"),
            ("response", "response_sha256"),
        ] {
            let (digest, size, _) = digest_file(&v0::confined(&cap.root, text(&item[field])?)?)?;
            need(digest == item[expected], "input changed during consumption")?;
            work.post_input_bytes += size;
        }
    }
    need(
        digest_file(manifest)?.0 == cap.sha
            && digest_file(&cap.root.join("plan.json"))?.0 == cap.m["plan_sha256"],
        "manifest/plan changed during consumption",
    )?;
    work.time("post_input_integrity", time);
    let cp_sha = digest_file(&cp_path)?.0;
    need(
        cp_sha == hash(&checkpoint(&identity, &entries))
            && v0::strict(&small(&id_path, 65536)?)? == identity,
        "state identity changed during run",
    )?;
    Ok(
        json!({"status":"COMPLETED_LOCAL_CAPTURE","schema":"sof-runtime.solana-incremental-run.v1",
        "mode":mode,"identity":identity,"checkpoint_sha256":cp_sha,"initial_committed_slots":initial,
        "total_slots":entries.len(),"projection_sha256":output_hash,"projection_bytes":work.aggregate_bytes,
        "projection_records":record_count,"work":work.value()}),
    )
}
fn main() {
    let args: Vec<String> = std::env::args().collect();
    let result = (|| -> Result<Value> {
        need(
            args.len() >= 4,
            "usage: MANIFEST STATE incremental|full_reproject [--checkpoint-sha256 SHA] [--pause POINT SLOT] [--forbid-prefix-decode]",
        )?;
        let mode = &args[3];
        need(
            mode == "incremental" || mode == "full_reproject",
            "unknown replay mode",
        )?;
        let (mut anchor, mut fault, mut forbid) = (None, None, false);
        let mut i = 4;
        while i < args.len() {
            match args[i].as_str() {
                "--checkpoint-sha256" if i + 1 < args.len() => {
                    need(anchor.is_none(), "duplicate anchor")?;
                    anchor = Some(args[i + 1].as_str());
                    i += 2;
                }
                "--pause" if i + 2 < args.len() => {
                    need(fault.is_none(), "duplicate pause")?;
                    let point = args[i + 1].clone();
                    need(
                        [
                            "partial_segment",
                            "segment_publish",
                            "partial_checkpoint",
                            "checkpoint_publish",
                            "partial_projection",
                            "projection_publish",
                        ]
                        .contains(&point.as_str()),
                        "unknown fault point",
                    )?;
                    fault = Some(Fault {
                        point,
                        slot: args[i + 2].parse::<u64>().map_err(|e| e.to_string())?,
                    });
                    i += 3;
                }
                "--forbid-prefix-decode" if !forbid => {
                    forbid = true;
                    i += 1;
                }
                _ => return Err("unknown/incomplete option".into()),
            }
        }
        execute(
            Path::new(&args[1]),
            Path::new(&args[2]),
            mode,
            anchor,
            fault,
            forbid,
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
