use fs2::FileExt;
use serde::de::{self, MapAccess, SeqAccess, Visitor};
use serde::{Deserialize, Deserializer};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fmt;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::time::Instant;

type Result<T> = std::result::Result<T, String>;
const PROJECTION: &str = "sof-runtime.solana-projection.v0";

struct Strict(Value);
impl<'de> Deserialize<'de> for Strict {
    fn deserialize<D: Deserializer<'de>>(d: D) -> std::result::Result<Self, D::Error> {
        struct V;
        impl<'de> Visitor<'de> for V {
            type Value = Strict;
            fn expecting(&self, f: &mut fmt::Formatter) -> fmt::Result {
                f.write_str("JSON without duplicate keys")
            }
            fn visit_bool<E: de::Error>(self, v: bool) -> std::result::Result<Strict, E> {
                Ok(Strict(json!(v)))
            }
            fn visit_i64<E: de::Error>(self, v: i64) -> std::result::Result<Strict, E> {
                Ok(Strict(json!(v)))
            }
            fn visit_u64<E: de::Error>(self, v: u64) -> std::result::Result<Strict, E> {
                Ok(Strict(json!(v)))
            }
            fn visit_f64<E: de::Error>(self, v: f64) -> std::result::Result<Strict, E> {
                serde_json::Number::from_f64(v)
                    .map(|x| Strict(Value::Number(x)))
                    .ok_or_else(|| E::custom("nonfinite JSON"))
            }
            fn visit_str<E: de::Error>(self, v: &str) -> std::result::Result<Strict, E> {
                Ok(Strict(json!(v)))
            }
            fn visit_string<E: de::Error>(self, v: String) -> std::result::Result<Strict, E> {
                Ok(Strict(json!(v)))
            }
            fn visit_unit<E: de::Error>(self) -> std::result::Result<Strict, E> {
                Ok(Strict(Value::Null))
            }
            fn visit_seq<A: SeqAccess<'de>>(
                self,
                mut a: A,
            ) -> std::result::Result<Strict, A::Error> {
                let mut v = Vec::new();
                while let Some(Strict(x)) = a.next_element()? {
                    v.push(x)
                }
                Ok(Strict(Value::Array(v)))
            }
            fn visit_map<A: MapAccess<'de>>(
                self,
                mut a: A,
            ) -> std::result::Result<Strict, A::Error> {
                let mut m = serde_json::Map::new();
                while let Some(k) = a.next_key::<String>()? {
                    if m.contains_key(&k) {
                        return Err(de::Error::custom("duplicate JSON key"));
                    }
                    let Strict(v) = a.next_value()?;
                    m.insert(k, v);
                }
                Ok(Strict(Value::Object(m)))
            }
        }
        d.deserialize_any(V)
    }
}

fn parse(raw: &[u8]) -> Result<Value> {
    serde_json::from_slice::<Strict>(raw)
        .map(|s| s.0)
        .map_err(|e| e.to_string())
}
fn need(ok: bool, why: &str) -> Result<()> {
    if ok { Ok(()) } else { Err(why.into()) }
}
fn hash(raw: &[u8]) -> String {
    format!("{:x}", Sha256::digest(raw))
}
fn encoded(v: &Value) -> Vec<u8> {
    serde_json::to_vec(v).unwrap()
}
fn object<'a>(v: &'a Value, key: &str) -> Result<&'a Value> {
    v.get(key).ok_or_else(|| format!("missing {key}"))
}
fn nat(v: &Value) -> Result<u64> {
    v.as_u64().ok_or("expected unsigned integer".into())
}
fn text(v: &Value) -> Result<&str> {
    v.as_str().ok_or("expected string".into())
}
fn array(v: &Value) -> Result<&Vec<Value>> {
    v.as_array().ok_or("expected array".into())
}
fn b58(v: &Value, size: Option<usize>) -> Result<String> {
    let s = text(v)?;
    need(s.len() <= 8192, "base58 size limit")?;
    let bytes = bs58::decode(s).into_vec().map_err(|e| e.to_string())?;
    need(
        size.is_none_or(|n| n == bytes.len()),
        "base58 decoded length",
    )?;
    Ok(s.to_owned())
}
fn keys(v: &Value) -> Result<Vec<String>> {
    array(v)?.iter().map(|v| b58(v, Some(32))).collect()
}
fn byte(v: &Value) -> Result<usize> {
    let n = nat(v)?;
    need(n <= 255, "u8 field")?;
    Ok(n as usize)
}
fn no_float(v: &Value) -> Result<()> {
    match v {
        Value::Number(n) => need(n.is_u64() || n.is_i64(), "nonintegral projected JSON"),
        Value::Array(a) => {
            for x in a {
                no_float(x)?;
            }
            Ok(())
        }
        Value::Object(m) => {
            for x in m.values() {
                no_float(x)?;
            }
            Ok(())
        }
        _ => Ok(()),
    }
}
fn config() -> Value {
    json!({"commitment":"finalized","encoding":"json","transactionDetails":"full","maxSupportedTransactionVersion":0,"rewards":false})
}

fn project_block(slot: u64, block: &Value) -> Result<Vec<Value>> {
    let txs = array(object(block, "transactions")?)?;
    let parent = nat(object(block, "parentSlot")?)?;
    need(parent < slot, "parent slot order")?;
    let height = object(block, "blockHeight")?;
    if !height.is_null() {
        nat(height)?;
    }
    let time = object(block, "blockTime")?;
    need(time.is_null() || time.as_i64().is_some(), "block time type")?;
    let mut records = vec![
        json!({"kind":"block","slot":slot,"blockhash":b58(object(block,"blockhash")?,Some(32))?,
        "previous_blockhash":b58(object(block,"previousBlockhash")?,Some(32))?,"parent_slot":parent,
        "block_height":height,"block_time":time,"transaction_count":txs.len()}),
    ];
    for (index, entry) in txs.iter().enumerate() {
        let version = object(entry, "version")?;
        let legacy = version.as_str() == Some("legacy");
        need(
            legacy || version.as_u64() == Some(0),
            "unsupported transaction version",
        )?;
        let tx = object(entry, "transaction")?;
        let message = object(tx, "message")?;
        let meta = object(entry, "meta")?;
        need(meta.is_object(), "missing full transaction metadata")?;
        let static_keys = keys(object(message, "accountKeys")?)?;
        let header = object(message, "header")?;
        let required = byte(object(header, "numRequiredSignatures")?)?;
        let signed = byte(object(header, "numReadonlySignedAccounts")?)?;
        let unsigned = byte(object(header, "numReadonlyUnsignedAccounts")?)?;
        need(
            required >= 1
                && required <= static_keys.len()
                && signed <= required
                && unsigned <= static_keys.len() - required,
            "header counts",
        )?;
        let signatures: Vec<String> = array(object(tx, "signatures")?)?
            .iter()
            .map(|v| b58(v, Some(64)))
            .collect::<Result<_>>()?;
        need(signatures.len() == required, "signature count")?;
        let empty = json!({"writable":[],"readonly":[]});
        let loaded = match meta.get("loadedAddresses") {
            Some(v) if !v.is_null() => v,
            _ if legacy => &empty,
            _ => return Err("missing v0 loaded addresses".into()),
        };
        let writable = keys(object(loaded, "writable")?)?;
        let readonly = keys(object(loaded, "readonly")?)?;
        let no_lookups = json!([]);
        let lookup = message.get("addressTableLookups").unwrap_or(&no_lookups);
        let lookup = array(lookup)?;
        need(
            !legacy || (lookup.is_empty() && writable.is_empty() && readonly.is_empty()),
            "legacy lookups",
        )?;
        let mut lookups = Vec::new();
        let (mut nw, mut nr) = (0, 0);
        for item in lookup {
            let w: Vec<usize> = array(object(item, "writableIndexes")?)?
                .iter()
                .map(byte)
                .collect::<Result<_>>()?;
            let r: Vec<usize> = array(object(item, "readonlyIndexes")?)?
                .iter()
                .map(byte)
                .collect::<Result<_>>()?;
            nw += w.len();
            nr += r.len();
            lookups.push(json!({"account_key":b58(object(item,"accountKey")?,Some(32))?,"writable_indexes":w,"readonly_indexes":r}));
        }
        need(
            nw == writable.len() && nr == readonly.len(),
            "loaded address counts",
        )?;
        let addresses: Vec<&String> = static_keys
            .iter()
            .chain(&writable)
            .chain(&readonly)
            .collect();
        need(addresses.len() <= 256, "account index width")?;
        let mut instructions = Vec::new();
        for item in array(object(message, "instructions")?)? {
            let program = byte(object(item, "programIdIndex")?)?;
            let accounts: Vec<usize> = array(object(item, "accounts")?)?
                .iter()
                .map(byte)
                .collect::<Result<_>>()?;
            need(
                program < addresses.len() && accounts.iter().all(|i| *i < addresses.len()),
                "instruction index out of range",
            )?;
            let resolved: Vec<&String> = accounts.iter().map(|i| addresses[*i]).collect();
            instructions.push(json!({"program_id_index":program,"program_id":addresses[program],"account_indices":accounts,"accounts":resolved,"data_base58":b58(object(item,"data")?,None)?}));
        }
        let error = object(meta, "err")?;
        no_float(error)?;
        records.push(json!({"kind":"transaction","slot":slot,"transaction_index":index,"version":version,"signatures":signatures,
            "fee":nat(object(meta,"fee")?)?,"error":error,"recent_blockhash":b58(object(message,"recentBlockhash")?,Some(32))?,
            "header":{"required_signatures":required,"readonly_signed":signed,"readonly_unsigned":unsigned},
            "static_keys":static_keys,"loaded_writable":writable,"loaded_readonly":readonly,"address_table_lookups":lookups,"instructions":instructions}));
    }
    Ok(records)
}

fn local(root: &Path, name: &str) -> Result<PathBuf> {
    need(
        !name.is_empty() && !name.contains(['/', '\\', ':']) && name != "." && name != "..",
        "nonlocal filename",
    )?;
    let p = root.join(name);
    let meta = fs::symlink_metadata(&p).map_err(|e| e.to_string())?;
    need(
        meta.is_file() && !meta.file_type().is_symlink(),
        "not a local regular file",
    )?;
    need(
        p.canonicalize().map_err(|e| e.to_string())?.parent() == Some(root),
        "file escapes root",
    )?;
    Ok(p)
}
fn rpc(root: &Path, item: &Value) -> Result<Value> {
    let request =
        fs::read(local(root, text(object(item, "request")?)?)?).map_err(|e| e.to_string())?;
    let raw =
        fs::read(local(root, text(object(item, "response")?)?)?).map_err(|e| e.to_string())?;
    need(
        request.len() <= 65536 && raw.len() <= 32 * 1024 * 1024,
        "RPC byte limit",
    )?;
    need(
        hash(&request) == item["request_sha256"] && hash(&raw) == item["response_sha256"],
        "capture byte identity mismatch",
    )?;
    let request = parse(&request)?;
    let reply = parse(&raw)?;
    need(
        request
            == json!({"jsonrpc":"2.0","id":item["id"],"method":item["method"],"params":item["params"]}),
        "bound request mismatch",
    )?;
    let id = nat(object(item, "id")?)?;
    need(
        reply["jsonrpc"] == "2.0"
            && nat(object(&reply, "id")?)? == id
            && reply.get("error").is_none(),
        "RPC error/envelope",
    )?;
    Ok(object(&reply, "result")?.clone())
}
struct Segment {
    slot: u64,
    bytes: Vec<u8>,
    records: usize,
}
fn capture(path: &Path) -> Result<(String, Vec<Segment>)> {
    need(
        !fs::symlink_metadata(path)
            .map_err(|e| e.to_string())?
            .file_type()
            .is_symlink(),
        "symlink manifest",
    )?;
    let raw = fs::read(path).map_err(|e| e.to_string())?;
    need(raw.len() <= 1024 * 1024, "manifest byte limit")?;
    let m = parse(&raw)?;
    let root = path
        .parent()
        .unwrap()
        .canonicalize()
        .map_err(|e| e.to_string())?;
    need(
        m["schema"] == "sof-runtime.solana-capture.v0"
            && m["projection"] == PROJECTION
            && m["config"] == config()
            && m["commitment"] == "finalized",
        "capture contract",
    )?;
    need(
        (m["capture_kind"] == "rpc_capture" || m["capture_kind"] == "synthetic_control")
            && m["finality_independently_verified"] == false,
        "capture provenance boundary",
    )?;
    let start = nat(object(&m, "start_slot")?)?;
    let end = nat(object(&m, "end_slot")?)?;
    need(
        end >= start && end - start < 16 && end < u64::MAX,
        "range limit",
    )?;
    let mut values = BTreeMap::new();
    for (role, item) in object(&m, "rpc")?.as_object().ok_or("RPC roles")? {
        values.insert(role.clone(), rpc(&root, item)?);
    }
    let blocks = array(object(&m, "listed_blocks")?)?;
    need(!blocks.is_empty(), "empty listed blocks")?;
    let slots: Vec<u64> = blocks
        .iter()
        .map(|b| nat(&b["slot"]))
        .collect::<Result<_>>()?;
    need(
        slots.windows(2).all(|s| s[0] < s[1]) && slots.iter().all(|s| start <= *s && *s <= end),
        "listed slot order/range",
    )?;
    let mut roles: BTreeSet<String> = [
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
    .collect();
    roles.extend(slots.iter().map(|s| format!("block-{s}")));
    need(
        values.keys().cloned().collect::<BTreeSet<_>>() == roles,
        "RPC inventory",
    )?;
    let call = |role: &str, method: &str, params: Value| -> Result<()> {
        need(
            m["rpc"][role]["method"] == method && m["rpc"][role]["params"] == params,
            "RPC role/config",
        )
    };
    for role in ["root_before", "root_after"] {
        call(role, "getSlot", json!([{"commitment":"finalized"}]))?;
        need(nat(&values[role])? >= end, "finalized root below range")?;
    }
    for role in ["index_before", "index_after"] {
        call(
            role,
            "getBlocks",
            json!([start,end,{"commitment":"finalized"}]),
        )?;
        need(values[role] == json!(slots), "captured index differs")?;
    }
    call("version", "getVersion", json!([]))?;
    need(
        values["version"] == m["server_version"] && values["version"]["solana-core"].is_string(),
        "version metadata",
    )?;
    for role in ["genesis", "genesis_after"] {
        call(role, "getGenesisHash", json!([]))?;
        need(
            values[role] == json!(b58(&m["genesis"], Some(32))?),
            "cluster mismatch",
        )?;
    }
    let mut previous = nat(&m["anchor"]["slot"])?;
    let mut previous_hash = b58(&m["anchor"]["blockhash"], Some(32))?;
    let mut anchor_config = config();
    anchor_config["transactionDetails"] = json!("none");
    call("anchor", "getBlock", json!([previous, anchor_config]))?;
    need(
        values["anchor"]["blockhash"] == previous_hash,
        "anchor mismatch",
    )?;
    let mut segments = Vec::new();
    for slot in start..=end {
        let block = blocks.iter().find(|b| b["slot"].as_u64() == Some(slot));
        let records = if let Some(item) = block {
            let role = format!("block-{slot}");
            need(item["role"] == role, "block role")?;
            call(&role, "getBlock", json!([slot, config()]))?;
            let data = &values[&role];
            let records = project_block(slot, data)?;
            need(
                data["blockhash"] == item["blockhash"]
                    && nat(&data["parentSlot"])? == previous
                    && data["previousBlockhash"] == previous_hash,
                "captured chain mismatch",
            )?;
            previous = slot;
            previous_hash = text(&data["blockhash"])?.to_owned();
            records
        } else {
            vec![json!({"kind":"not_listed_by_source","slot":slot})]
        };
        let mut bytes = Vec::new();
        for record in &records {
            bytes.extend(encoded(record));
            bytes.push(b'\n');
        }
        segments.push(Segment {
            slot,
            bytes,
            records: records.len(),
        });
    }
    Ok((hash(&raw), segments))
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
        let _ = std::io::stdout().flush();
        loop {
            std::thread::sleep(std::time::Duration::from_millis(100));
        }
    }
}
fn check_regular(path: &Path) -> Result<()> {
    let meta = fs::symlink_metadata(path).map_err(|e| e.to_string())?;
    need(
        meta.is_file() && !meta.file_type().is_symlink(),
        "state member not regular",
    )
}
fn remove_temp(path: &Path) -> Result<()> {
    if path.exists() {
        check_regular(path)?;
        fs::remove_file(path).map_err(|e| e.to_string())?;
    }
    Ok(())
}
fn publish(
    path: &Path,
    bytes: &[u8],
    temp: &Path,
    fault: &Option<Fault>,
    partial: &str,
    slot: u64,
) -> Result<()> {
    remove_temp(temp)?;
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(temp)
        .map_err(|e| e.to_string())?;
    let half = bytes.len() / 2;
    file.write_all(&bytes[..half]).map_err(|e| e.to_string())?;
    file.sync_all().map_err(|e| e.to_string())?;
    pause(fault, partial, slot);
    file.write_all(&bytes[half..]).map_err(|e| e.to_string())?;
    file.sync_all().map_err(|e| e.to_string())?;
    drop(file);
    fs::rename(temp, path).map_err(|e| e.to_string())?;
    Ok(())
}
fn segment_path(root: &Path, slot: u64) -> PathBuf {
    root.join(format!("slot-{slot}.jsonl"))
}
fn checkpoint(identity: &Value, committed: &[Value]) -> Value {
    json!({"schema":"sof-runtime.solana-checkpoint.v0","identity":identity,"next_index":committed.len(),"committed":committed})
}

fn execute(manifest: &Path, output: &Path, fault: Option<Fault>) -> Result<Value> {
    let start = Instant::now();
    let (manifest_sha, segments) = capture(manifest)?;
    let decoded = start.elapsed().as_secs_f64();
    let binary =
        fs::read(std::env::current_exe().map_err(|e| e.to_string())?).map_err(|e| e.to_string())?;
    let commit_start = Instant::now();
    let identity = json!({"manifest_sha256":manifest_sha,"projection":PROJECTION,"executable_sha256":hash(&binary)});
    if !output.exists() {
        fs::create_dir_all(output).map_err(|e| e.to_string())?;
    }
    need(
        !fs::symlink_metadata(output)
            .map_err(|e| e.to_string())?
            .file_type()
            .is_symlink(),
        "symlink state root",
    )?;
    let root = output.canonicalize().map_err(|e| e.to_string())?;
    let lock_path = root.join("writer.lock");
    if lock_path.exists() {
        check_regular(&lock_path)?;
    }
    let lock = OpenOptions::new()
        .read(true)
        .write(true)
        .create(true)
        .truncate(false)
        .open(&lock_path)
        .map_err(|e| e.to_string())?;
    lock.try_lock_exclusive()
        .map_err(|_| "state directory already has a writer")?;
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
    for segment in &segments {
        allowed.insert(format!("slot-{}.jsonl", segment.slot));
        allowed.insert(format!("slot-{}.tmp", segment.slot));
    }
    for member in fs::read_dir(&root).map_err(|e| e.to_string())? {
        let member = member.map_err(|e| e.to_string())?;
        need(
            allowed.contains(&member.file_name().to_string_lossy().to_string()),
            "foreign state file",
        )?;
        check_regular(&member.path())?;
    }
    let id_path = root.join("identity.json");
    let cp_path = root.join("checkpoint.json");
    if id_path.exists() {
        need(
            parse(&fs::read(&id_path).map_err(|e| e.to_string())?)? == identity,
            "state identity mismatch",
        )?;
    } else {
        need(
            !cp_path.exists()
                && segments
                    .iter()
                    .all(|s| !segment_path(&root, s.slot).exists()),
            "state without identity",
        )?;
        publish(
            &id_path,
            &encoded(&identity),
            &root.join("identity.tmp"),
            &None,
            "",
            0,
        )?;
    }
    let mut committed = Vec::new();
    if cp_path.exists() {
        let cp = parse(&fs::read(&cp_path).map_err(|e| e.to_string())?)?;
        need(
            cp["schema"] == "sof-runtime.solana-checkpoint.v0" && cp["identity"] == identity,
            "checkpoint identity",
        )?;
        committed = array(object(&cp, "committed")?)?.clone();
        need(
            nat(object(&cp, "next_index")?)? == committed.len() as u64
                && committed.len() <= segments.len(),
            "checkpoint cursor/prefix",
        )?;
    } else {
        need(
            segments
                .iter()
                .all(|s| !segment_path(&root, s.slot).exists()),
            "segments without initial checkpoint",
        )?;
        publish(
            &cp_path,
            &encoded(&checkpoint(&identity, &[])),
            &root.join("checkpoint.tmp"),
            &None,
            "",
            0,
        )?;
    }
    for (i, item) in committed.iter().enumerate() {
        let s = &segments[i];
        let expected = json!({"slot":s.slot,"sha256":hash(&s.bytes),"records":s.records});
        need(*item == expected, "checkpoint member/prefix mismatch")?;
        let p = segment_path(&root, s.slot);
        check_regular(&p)?;
        need(
            fs::read(p).map_err(|e| e.to_string())? == s.bytes,
            "committed segment corruption",
        )?;
    }
    let resumed_from = committed.len();
    let mut adopted = 0;
    for (i, s) in segments.iter().enumerate().skip(resumed_from) {
        need(
            segments
                .iter()
                .skip(i + 1)
                .all(|later| !segment_path(&root, later.slot).exists()),
            "noncontiguous uncommitted segment",
        )?;
        let path = segment_path(&root, s.slot);
        if path.exists() {
            check_regular(&path)?;
            need(
                fs::read(&path).map_err(|e| e.to_string())? == s.bytes,
                "orphan segment mismatch",
            )?;
            adopted += 1;
        } else {
            publish(
                &path,
                &s.bytes,
                &root.join(format!("slot-{}.tmp", s.slot)),
                &fault,
                "partial_segment",
                s.slot,
            )?;
        }
        pause(&fault, "segment_publish", s.slot);
        committed.push(json!({"slot":s.slot,"sha256":hash(&s.bytes),"records":s.records}));
        publish(
            &cp_path,
            &encoded(&checkpoint(&identity, &committed)),
            &root.join("checkpoint.tmp"),
            &fault,
            "partial_checkpoint",
            s.slot,
        )?;
        pause(&fault, "checkpoint_publish", s.slot);
    }
    let mut all = Vec::new();
    for s in &segments {
        all.extend(&s.bytes);
        remove_temp(&root.join(format!("slot-{}.tmp", s.slot)))?;
    }
    remove_temp(&root.join("checkpoint.tmp"))?;
    remove_temp(&root.join("identity.tmp"))?;
    let projection = root.join("projection.jsonl");
    let last = segments.last().unwrap().slot;
    if projection.exists() {
        need(
            fs::read(&projection).map_err(|e| e.to_string())? == all,
            "aggregate corruption",
        )?;
        remove_temp(&root.join("projection.tmp"))?;
    } else {
        publish(
            &projection,
            &all,
            &root.join("projection.tmp"),
            &fault,
            "partial_projection",
            last,
        )?;
    }
    pause(&fault, "projection_publish", last);
    let commit_seconds = commit_start.elapsed().as_secs_f64();
    let post = Instant::now();
    let (end_sha, end_segments) = capture(manifest)?;
    need(
        end_sha == manifest_sha
            && end_segments
                .iter()
                .zip(&segments)
                .all(|(a, b)| a.bytes == b.bytes),
        "capture changed during execution",
    )?;
    Ok(
        json!({"status":"COMPLETED_LOCAL_CAPTURE","manifest_sha256":manifest_sha,"projection_sha256":hash(&all),
        "projection_bytes":all.len(),"records":segments.iter().map(|s|s.records).sum::<usize>(),"slots":segments.len(),
        "resumed_from_index":resumed_from,"orphan_segments_adopted":adopted,"decode_validate_project_seconds":decoded,
        "identity_lock_checkpoint_aggregate_seconds":commit_seconds,"post_capture_validation_seconds":post.elapsed().as_secs_f64(),"whole_internal_seconds":start.elapsed().as_secs_f64(),"independent_finality_verification":false,
        "power_loss_durability_claimed":false,"external_sink_exactly_once_claimed":false}),
    )
}
fn main() {
    let result = (|| -> Result<Value> {
        let args: Vec<String> = std::env::args().collect();
        need(
            args.len() == 3 || args.len() == 6,
            "usage: MANIFEST STATE_DIR [--pause POINT SLOT]",
        )?;
        let fault = if args.len() == 6 {
            need(args[3] == "--pause", "unknown option")?;
            Some(Fault {
                point: args[4].clone(),
                slot: args[5].parse().map_err(|_| "fault slot")?,
            })
        } else {
            None
        };
        execute(Path::new(&args[1]), Path::new(&args[2]), fault)
    })();
    match result {
        Ok(value) => println!("{value}"),
        Err(error) => {
            println!("{}", json!({"status":"UNRESOLVED","detail":error}));
            std::process::exit(2);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn duplicate_keys_are_not_a_second_interpretation() {
        assert!(parse(br#"{"outer":{"key":1,"key":2}}"#).is_err());
        assert!(parse(br#"{"unused_rpc_field":1.25}"#).is_ok());
        assert!(no_float(&json!({"projected_error":1.25})).is_err());
    }

    #[test]
    fn integer_and_address_checks_do_not_coerce_types() {
        assert!(nat(&json!(true)).is_err());
        assert!(nat(&json!(1.0)).is_err());
        assert!(b58(&json!("1".repeat(32)), Some(32)).is_ok());
        assert!(b58(&json!("1".repeat(31)), Some(32)).is_err());
    }
}
