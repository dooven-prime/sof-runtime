use fs2::FileExt;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};

#[allow(dead_code)]
mod validation {
    include!("../../solana-source-advancement/src/main.rs");
    pub fn calculate(request: &Path, destination: &Path) -> serde_json::Value {
        frozen::advance(request, destination)
    }
}

type Result<T> = std::result::Result<T, String>;
fn need(ok: bool, reason: &str) -> Result<()> {
    if ok { Ok(()) } else { Err(reason.into()) }
}
fn raw(v: &Value) -> Vec<u8> {
    serde_json::to_vec(v).unwrap()
}
fn hash(b: &[u8]) -> String {
    format!("{:x}", Sha256::digest(b))
}
fn text(v: &Value) -> Result<&str> {
    v.as_str().ok_or("STRING_REQUIRED".into())
}
fn regular(p: &Path) -> Result<()> {
    let m = fs::symlink_metadata(p).map_err(|e| e.to_string())?;
    need(
        m.is_file() && !m.file_type().is_symlink(),
        "REGULAR_FILE_REQUIRED",
    )
}
fn directory(p: &Path) -> Result<()> {
    let m = fs::symlink_metadata(p).map_err(|e| e.to_string())?;
    need(
        m.is_dir() && !m.file_type().is_symlink(),
        "DIRECTORY_REQUIRED",
    )
}
fn read(p: &Path) -> Result<Vec<u8>> {
    regular(p)?;
    fs::read(p).map_err(|e| e.to_string())
}
fn digest(p: &Path) -> Result<String> {
    regular(p)?;
    // Windows byte-range locking disallows reopening this lock for reading.
    // It is a protocol-empty file, so its length proves its exact byte value.
    if p.file_name().is_some_and(|n| n == "writer.lock")
        && fs::metadata(p).map_err(|e| e.to_string())?.len() == 0
    {
        return Ok(hash(b""));
    }
    let mut f = File::open(p).map_err(|e| e.to_string())?;
    let mut h = Sha256::new();
    let mut b = [0; 65536];
    loop {
        let n = f.read(&mut b).map_err(|e| e.to_string())?;
        if n == 0 {
            break;
        }
        h.update(&b[..n]);
    }
    Ok(format!("{:x}", h.finalize()))
}
fn inventory(root: &Path) -> Result<BTreeMap<String, String>> {
    directory(root)?;
    let mut out = BTreeMap::new();
    for item in fs::read_dir(root).map_err(|e| e.to_string())? {
        let item = item.map_err(|e| e.to_string())?;
        let name = item
            .file_name()
            .to_str()
            .ok_or("NON_UTF8_NAME")?
            .to_string();
        out.insert(name, digest(&item.path())?);
    }
    Ok(out)
}
fn lock(p: &Path) -> Result<File> {
    if p.exists() {
        regular(p)?;
    }
    let f = OpenOptions::new()
        .read(true)
        .write(true)
        .create(true)
        .truncate(false)
        .open(p)
        .map_err(|e| e.to_string())?;
    f.try_lock_exclusive()
        .map_err(|_| "PUBLICATION_WRITER_CONFLICT".to_string())?;
    Ok(f)
}
fn clear_scratch(p: &Path, depth: u8) -> Result<()> {
    // Only the operation-owned calculation subtree is disposable; stages are evidence.
    need(depth <= 3, "SCRATCH_DEPTH")?;
    directory(p)?;
    for item in fs::read_dir(p).map_err(|e| e.to_string())? {
        let path = item.map_err(|e| e.to_string())?.path();
        let m = fs::symlink_metadata(&path).map_err(|e| e.to_string())?;
        need(!m.file_type().is_symlink(), "SCRATCH_SYMLINK")?;
        if m.is_dir() {
            clear_scratch(&path, depth + 1)?;
        } else {
            regular(&path)?;
            fs::remove_file(path).map_err(|e| e.to_string())?;
        }
    }
    fs::remove_dir(p).map_err(|e| e.to_string())
}

struct Fault {
    point: String,
    marker: Option<PathBuf>,
    intent: String,
}
impl Fault {
    fn pause(&self, point: &str) -> Result<()> {
        if self.point != point {
            return Ok(());
        }
        let marker = self.marker.as_ref().ok_or("FAULT_MARKER_REQUIRED")?;
        let mut f = OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(marker)
            .map_err(|e| e.to_string())?;
        f.write_all(&raw(
            &json!({"point":point,"pid":std::process::id(),"intent_sha256":self.intent}),
        ))
        .and_then(|_| f.sync_all())
        .map_err(|e| e.to_string())?;
        drop(f);
        loop {
            std::thread::sleep(std::time::Duration::from_millis(50));
        }
    }
}

fn ensure_file(root: &Path, name: &str, expected: &[u8], kind: &str, fault: &Fault) -> Result<()> {
    let final_path = root.join(name);
    let pending = root.join(format!("{name}.pending"));
    if final_path.exists() {
        need(read(&final_path)? == expected, "FINAL_FILE_MISMATCH")?;
        need(!pending.exists(), "FINAL_AND_PENDING_COEXIST")?;
        return Ok(());
    }
    let prefix = if pending.exists() {
        read(&pending)?
    } else {
        Vec::new()
    };
    need(expected.starts_with(&prefix), "PENDING_NOT_EXPECTED_PREFIX")?;
    let mut f = OpenOptions::new()
        .create(true)
        .append(true)
        .open(&pending)
        .map_err(|e| e.to_string())?;
    let split = prefix.len().max(expected.len() / 2);
    f.write_all(&expected[prefix.len()..split])
        .and_then(|_| f.sync_all())
        .map_err(|e| e.to_string())?;
    fault.pause(&format!("{kind}_partial"))?;
    f.write_all(&expected[split..])
        .and_then(|_| f.sync_all())
        .map_err(|e| e.to_string())?;
    drop(f);
    fs::rename(pending, final_path).map_err(|e| e.to_string())?;
    fault.pause(&format!("{kind}_published"))
}

fn snapshot(req_path: &Path, req: &Value) -> Result<BTreeMap<String, String>> {
    let mut all = BTreeMap::new();
    for path in [req_path, Path::new(text(&req["policy_path"])?)] {
        all.insert(
            path.canonicalize()
                .map_err(|e| e.to_string())?
                .to_string_lossy()
                .to_string(),
            digest(path)?,
        );
    }
    for field in ["candidate_manifest", "old_manifest", "old_state"] {
        if req[field].is_null() {
            continue;
        }
        let path = Path::new(text(&req[field])?);
        let root = if field == "old_state" {
            path
        } else {
            path.parent().ok_or("CAPTURE_PARENT")?
        };
        directory(root)?;
        let root = root.canonicalize().map_err(|e| e.to_string())?;
        for (name, sha) in inventory(&root)? {
            all.insert(root.join(name).to_string_lossy().to_string(), sha);
        }
    }
    Ok(all)
}

fn recover(req_path: &Path, destination: &Path, mut fault: Fault) -> Result<Value> {
    let req_bytes = read(req_path)?;
    need(req_bytes.len() <= 65536, "REQUEST_SIZE")?;
    let req: Value = serde_json::from_slice(&req_bytes).map_err(|e| e.to_string())?;
    need(destination.is_absolute(), "ABSOLUTE_DESTINATION_REQUIRED")?;
    let parent = destination
        .parent()
        .ok_or("DESTINATION_PARENT")?
        .canonicalize()
        .map_err(|e| e.to_string())?;
    let name = destination
        .file_name()
        .and_then(|s| s.to_str())
        .ok_or("DESTINATION_NAME")?;
    let destination = parent.join(name);
    let mut protected = Vec::new();
    for field in ["candidate_manifest", "old_manifest", "old_state"] {
        if req[field].is_null() {
            continue;
        }
        let p = Path::new(text(&req[field])?);
        let p = if field == "old_state" {
            p
        } else {
            p.parent().ok_or("INPUT_PARENT")?
        };
        let p = p.canonicalize().map_err(|e| e.to_string())?;
        need(
            !parent.starts_with(&p),
            "DESTINATION_INSIDE_INPUT_OR_PARENT",
        )?;
        protected.push(p);
    }
    let control = parent.join(format!(".{name}.publication-v0"));
    if let Some(marker) = &fault.marker {
        let mparent = marker
            .parent()
            .ok_or("MARKER_PARENT")?
            .canonicalize()
            .map_err(|e| e.to_string())?;
        need(
            !protected.iter().any(|p| mparent.starts_with(p))
                && !mparent.starts_with(&control)
                && !mparent.starts_with(&destination),
            "UNSAFE_FAULT_MARKER",
        )?;
    }
    let inputs = snapshot(req_path, &req)?;
    let intent = raw(
        &json!({"schema":"sof-runtime.publication-intent.v0", "request_sha256":hash(&req_bytes),
        "executable_sha256":digest(&std::env::current_exe().map_err(|e| e.to_string())?)?,
        "destination":destination, "input_inventory":inputs}),
    );
    fault.intent = hash(&intent);
    let _output_lock = lock(&parent.join(format!(".{name}.publication-v0.lock")))?;
    let had_intent = control.join("intent.json").exists();
    if destination.exists() {
        directory(&destination)?;
        need(
            had_intent && control.join("ready.json").exists(),
            "UNOWNED_OR_INCOMPLETE_PUBLICATION",
        )?;
    }
    if !control.exists() {
        fs::create_dir(&control).map_err(|e| e.to_string())?;
    }
    directory(&control)?;
    let allowed: BTreeSet<&str> = [
        "intent.json",
        "intent.json.pending",
        "calculation",
        "stage",
        "ready.json",
        "ready.json.pending",
        "receipt.json",
        "receipt.json.pending",
    ]
    .into_iter()
    .collect();
    for item in fs::read_dir(&control).map_err(|e| e.to_string())? {
        let item = item.map_err(|e| e.to_string())?;
        need(
            allowed.contains(item.file_name().to_str().ok_or("CONTROL_NAME")?),
            "FOREIGN_CONTROL_FILE",
        )?;
        need(
            !item.file_type().map_err(|e| e.to_string())?.is_symlink(),
            "CONTROL_SYMLINK",
        )?;
        if !had_intent {
            need(
                item.file_name() == "intent.json.pending",
                "MISSING_INTENT_WITH_ARTIFACTS",
            )?;
        }
    }
    ensure_file(&control, "intent.json", &intent, "intent", &fault)?;

    let calculation = control.join("calculation");
    if calculation.exists() {
        clear_scratch(&calculation, 0)?;
    }
    fs::create_dir(&calculation).map_err(|e| e.to_string())?;
    fault.pause("calculation_started")?;
    let model = calculation.join("model");
    let result = validation::calculate(req_path, &model);
    if result["status"] != "COMPLETED_OFFLINE_ADVANCEMENT" {
        return Ok(
            json!({"schema":"sof-runtime.publication-result.v0","status":result["status"],
            "publication_confirmed":false,"reason":result["reason"],"advancement":result}),
        );
    }
    fault.pause("calculation_completed")?;
    let expected = inventory(&model)?;
    let _parent_lock = if !req["old_state"].is_null() {
        // The semantic validator held this lock during calculation; reacquire and
        // compare all original bytes before making any publication decision.
        let p = Path::new(text(&req["old_state"])?).join("writer.lock");
        regular(&p)?;
        Some(lock(&p)?)
    } else {
        None
    };
    need(snapshot(req_path, &req)? == inputs, "BOUND_INPUTS_CHANGED")?;
    let already_published = destination.exists();
    let mut resumed_stage = false;
    if !already_published {
        let stage = control.join("stage");
        resumed_stage = stage.exists();
        if !stage.exists() {
            fs::create_dir(&stage).map_err(|e| e.to_string())?;
        }
        directory(&stage)?;
        fault.pause("stage_created")?;
        let allowed: BTreeSet<String> = expected
            .keys()
            .flat_map(|s| [s.clone(), format!("{s}.pending")])
            .collect();
        for item in fs::read_dir(&stage).map_err(|e| e.to_string())? {
            let item = item.map_err(|e| e.to_string())?;
            need(
                allowed.contains(&item.file_name().to_string_lossy().to_string()),
                "FOREIGN_STAGE_FILE",
            )?;
            regular(&item.path())?;
        }
        for name in expected.keys().filter(|s| s.starts_with("slot-")) {
            ensure_file(&stage, name, &read(&model.join(name))?, "segment", &fault)?;
        }
        for (name, kind) in [
            ("projection.jsonl", "projection"),
            ("transition.json", "transition"),
            ("checkpoint.json", "checkpoint"),
            ("writer.lock", "writer"),
        ] {
            ensure_file(&stage, name, &read(&model.join(name))?, kind, &fault)?;
        }
        need(inventory(&stage)? == expected, "STAGE_INVENTORY_MISMATCH")?;
    } else {
        need(
            !control.join("stage").exists(),
            "PUBLISHED_AND_STAGE_COEXIST",
        )?;
        need(
            inventory(&destination)? == expected,
            "PUBLISHED_INVENTORY_MISMATCH",
        )?;
    }
    let ready = raw(
        &json!({"schema":"sof-runtime.publication-ready.v0","intent_sha256":hash(&intent),
        "files":expected,"advancement":result}),
    );
    ensure_file(&control, "ready.json", &ready, "ready", &fault)?;
    need(
        snapshot(req_path, &req)? == inputs,
        "BOUND_INPUTS_CHANGED_BEFORE_PUBLICATION",
    )?;
    if !already_published {
        fault.pause("before_publication")?;
        need(!destination.exists(), "DESTINATION_APPEARED")?;
        fs::rename(control.join("stage"), &destination).map_err(|e| e.to_string())?;
        fault.pause("after_publication")?;
    }
    need(
        inventory(&destination)? == expected,
        "PUBLISHED_INVENTORY_MISMATCH",
    )?;
    need(
        snapshot(req_path, &req)? == inputs,
        "BOUND_INPUTS_CHANGED_AFTER_PUBLICATION",
    )?;
    let receipt = raw(
        &json!({"schema":"sof-runtime.publication-receipt.v0","status":"COMPLETED_RECOVERABLE_PUBLICATION",
        "intent_sha256":hash(&intent),"ready_sha256":hash(&ready),"destination":destination,
        "files":expected,"advancement":result}),
    );
    ensure_file(&control, "receipt.json", &receipt, "receipt", &fault)?;
    Ok(
        json!({"schema":"sof-runtime.publication-result.v0","status":"COMPLETED_RECOVERABLE_PUBLICATION",
        "publication_confirmed":true,"receipt_sha256":hash(&receipt),"intent_sha256":hash(&intent),
        "recovery":if already_published {"REPLAYED_PUBLISHED"} else if resumed_stage {"RECOVERED_STAGE"} else {"COMMITTED_NEW"},
        "semantic_recalculation":true,"advancement":result}),
    )
}

fn main() {
    let a: Vec<String> = std::env::args().collect();
    let output = if a.len() == 3 || (a.len() == 6 && a[3] == "--pause") {
        let fault = Fault {
            point: a.get(4).cloned().unwrap_or_default(),
            marker: a.get(5).map(PathBuf::from),
            intent: String::new(),
        };
        recover(Path::new(&a[1]), Path::new(&a[2]), fault)
    } else {
        Err("usage: REQUEST OUTPUT [--pause POINT MARKER]".into())
    };
    match output {
        Ok(v) => {
            println!("{v}");
            if v["publication_confirmed"] != true {
                std::process::exit(2);
            }
        }
        Err(e) => {
            println!(
                "{}",
                json!({"schema":"sof-runtime.publication-result.v0","status":"UNRESOLVED",
                "publication_confirmed":false,"reason":e})
            );
            std::process::exit(2);
        }
    }
}
