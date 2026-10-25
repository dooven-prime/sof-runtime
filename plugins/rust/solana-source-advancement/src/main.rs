use serde_json::json;
use std::path::Path;

#[allow(dead_code)]
mod frozen {
    include!("../../solana-incremental-replay/src/main.rs");

    struct Bundle {
        cap: Capture,
        source: Value,
        credential_sha: String,
        evidence: Vec<(PathBuf, String)>,
    }
    fn has(list: &Value, value: &str) -> Result<bool> {
        Ok(arr(list)?.iter().any(|v| v.as_str() == Some(value)))
    }
    fn bundle(path: &Path, policy: &Value) -> Result<Bundle> {
        let cap = Capture::load(path).map_err(|e| format!("CAPTURE_EVIDENCE_INVALID: {e}"))?;
        need(
            cap.m["capture_kind"] == "synthetic_control"
                && cap.m["offline_derivation"]["upstream_manifest_sha256"]
                    == policy["upstream_manifest_sha256"]
                && cap.m["offline_derivation"]["not_an_rpc_capture"] == true,
            "OFFLINE_CAPTURE_DERIVATION_REQUIRED",
        )?;
        need(
            cap.root.join("credential.json").exists(),
            "SOURCE_CREDENTIAL_EVIDENCE_MISSING",
        )?;
        let cp = v0::confined(&cap.root, "credential.json")?;
        let credential_raw = small(&cp, 65536)?;
        let credential_sha = hash(&credential_raw);
        let c = v0::strict(&credential_raw)?;
        need(
            c["schema"] == "sof-runtime.offline-source-credential.v0"
                && c["genesis"] == cap.m["genesis"]
                && c["genesis"] == policy["genesis"]
                && c["locator"] == cap.m["source"]
                && text(&c["locator"])?.starts_with("offline://")
                && c["evidence_class"] == "LOCAL_DERIVED_CAPTURE_FIXTURE"
                && c["provider_authentication_claimed"] == false
                && nat(&c["scope"]["start_slot"])? <= cap.start
                && nat(&c["scope"]["end_slot"])? >= cap.end
                && !text(&c["revision"])?.is_empty(),
            "SOURCE_CREDENTIAL_BINDING",
        )?;
        need(
            has(&policy["credential_sha256"], &credential_sha)?,
            "SOURCE_CREDENTIAL_NOT_ALLOWED",
        )?;
        need(
            cap.root.join("admission.json").exists(),
            "CAPTURE_ADMISSION_EVIDENCE_MISSING",
        )?;
        let ap = v0::confined(&cap.root, "admission.json")?;
        let admission_raw = small(&ap, 65536)?;
        let admission_sha = hash(&admission_raw);
        let a = v0::strict(&admission_raw)?;
        need(
            a["schema"] == "sof-runtime.offline-capture-admission.v0"
                && a["manifest_sha256"] == cap.sha
                && a["credential_sha256"] == credential_sha
                && a["upstream_manifest_sha256"] == policy["upstream_manifest_sha256"]
                && a["qualification"] == "LOCAL_TEST_PERMISSION_NOT_PROVIDER_TRUST",
            "CAPTURE_ADMISSION_BINDING",
        )?;
        need(
            has(&policy["admission_sha256"], &admission_sha)?,
            "CAPTURE_ADMISSION_NOT_ALLOWED",
        )?;
        let source = json!({"schema":"sof-runtime.source-identity.v0","credential_sha256":credential_sha,
            "locator":c["locator"],"genesis":c["genesis"],"evidence_class":c["evidence_class"]});
        Ok(Bundle {
            cap,
            source,
            credential_sha,
            evidence: vec![(cp, hash(&credential_raw)), (ap, admission_sha)],
        })
    }
    fn stable(b: &Bundle, manifest: &Path) -> Result<u64> {
        let mut total = 0;
        for item in b.cap.m["rpc"].as_object().unwrap().values() {
            for (field, expected) in [
                ("request", "request_sha256"),
                ("response", "response_sha256"),
            ] {
                let (digest, size, _) =
                    digest_file(&v0::confined(&b.cap.root, text(&item[field])?)?)?;
                need(digest == item[expected], "SOURCE_BYTES_CHANGED_OR_MISSING")?;
                total += size;
            }
        }
        need(
            digest_file(manifest)?.0 == b.cap.sha
                && digest_file(&b.cap.root.join("plan.json"))?.0 == b.cap.m["plan_sha256"],
            "CAPTURE_IDENTITY_CHANGED",
        )?;
        for (path, expected) in &b.evidence {
            need(digest_file(path)?.0 == *expected, "SOURCE_EVIDENCE_CHANGED")?;
        }
        Ok(total)
    }
    fn work_report(w: &Work, candidate_prefix_bytes: u64) -> Value {
        json!({"old_prefix_decoded_slots":[],"candidate_prefix_decoded_slots":w.prefix_slots,
            "candidate_suffix_decoded_slots":w.suffix_slots,"prefix_decode_bytes":w.prefix_decode_bytes,
            "suffix_decode_bytes":w.suffix_decode_bytes,"old_prefix_verified_input_bytes":w.prefix_input_bytes,
            "candidate_prefix_verified_input_bytes":candidate_prefix_bytes,"old_verified_segment_bytes":w.prefix_segment_bytes,
            "post_verified_rpc_bytes":w.post_input_bytes,"staged_new_slots":w.newly_committed_slots,"aggregate_bytes":w.aggregate_bytes})
    }
    fn frame(body: &Value) -> Vec<u8> {
        bytes(&json!({"body":body,"body_sha256":hash(&bytes(body))}))
    }
    fn write_new(path: &Path, raw: &[u8]) -> Result<()> {
        let mut file = OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(path)
            .map_err(|e| e.to_string())?;
        file.write_all(raw)
            .and_then(|_| file.sync_all())
            .map_err(|e| e.to_string())
    }
    struct Stage {
        root: PathBuf,
        published: bool,
    }
    impl Drop for Stage {
        fn drop(&mut self) {
            if !self.published
                && let Ok(items) = fs::read_dir(&self.root)
            {
                for item in items.flatten() {
                    if let Ok(m) = fs::symlink_metadata(item.path())
                        && m.is_file()
                        && !m.file_type().is_symlink()
                    {
                        let _ = fs::remove_file(item.path());
                    }
                }
                let _ = fs::remove_dir(&self.root);
            }
        }
    }
    fn empty_result() -> Value {
        json!({"schema":"sof-runtime.source-transition-result.v0","status":"UNRESOLVED","published":false,
            "request_sha256":null,"source_transition":{"from":null,"to":null},"execution_identity":null,
            "affected_checkpoint_sha256":null,"new_checkpoint_sha256":null,"earliest_conflict_slot":null,
            "compatibility":"NOT_ESTABLISHED","reason":null,"work":null})
    }

    pub fn advance(request_path: &Path, destination: &Path) -> Value {
        let mut result = empty_result();
        let decision = (|| -> Result<()> {
            let request_raw = small(request_path, 65536)?;
            let req = v0::strict(&request_raw)?;
            result["request_sha256"] = json!(hash(&request_raw));
            result["requested_parent_checkpoint_sha256"] = req["old_checkpoint_sha256"].clone();
            let expected: BTreeSet<String> = [
                "schema",
                "mode",
                "policy_path",
                "policy_sha256",
                "candidate_manifest",
                "old_manifest",
                "old_state",
                "old_checkpoint_sha256",
            ]
            .iter()
            .map(|x| x.to_string())
            .collect();
            need(
                req.as_object()
                    .ok_or("REQUEST_OBJECT")?
                    .keys()
                    .cloned()
                    .collect::<BTreeSet<_>>()
                    == expected,
                "REQUEST_FIELDS",
            )?;
            need(
                req["schema"] == "sof-runtime.source-advancement-request.v0",
                "REQUEST_SCHEMA",
            )?;
            let mode = text(&req["mode"])?;
            need(
                ["init", "append", "reapprove"].contains(&mode),
                "REQUEST_MODE",
            )?;
            if mode == "init" {
                need(
                    req["old_manifest"].is_null()
                        && req["old_state"].is_null()
                        && req["old_checkpoint_sha256"].is_null(),
                    "INIT_HAS_PARENT",
                )?;
            }
            let policy_path = Path::new(text(&req["policy_path"])?);
            let policy_raw = small(policy_path, 1024 * 1024)?;
            let policy_sha = hash(&policy_raw);
            need(req["policy_sha256"] == policy_sha, "POLICY_ANCHOR_MISMATCH")?;
            let policy = v0::strict(&policy_raw)?;
            need(
                policy["schema"] == "sof-runtime.offline-source-policy.v0"
                    && policy["projection"] == PROJECTION
                    && policy["scope"] == "OFFLINE_FIXED_CAPTURE_COMPATIBILITY_ONLY",
                "POLICY_CONTRACT",
            )?;
            let execution = json!({"schema":"sof-runtime.execution-identity.v0","projection":PROJECTION,
                "program_sha256":digest_file(&std::env::current_exe().map_err(|e|e.to_string())?)?.0,"policy_sha256":policy_sha});
            result["execution_identity"] = execution.clone();
            let candidate_path = Path::new(text(&req["candidate_manifest"])?);
            let candidate = bundle(candidate_path, &policy)?;
            result["source_transition"]["to"] = candidate.source.clone();
            need(destination.is_absolute(), "DESTINATION_MUST_BE_ABSOLUTE")?;
            let parent = destination
                .parent()
                .ok_or("DESTINATION_PARENT")?
                .canonicalize()
                .map_err(|e| e.to_string())?;
            need(
                !parent.starts_with(&candidate.cap.root),
                "DESTINATION_INSIDE_CAPTURE",
            )?;
            // Reject input-directory aliases before creating even a sibling lock file.
            if mode != "init" {
                let previous_state = Path::new(text(&req["old_state"])?)
                    .canonicalize()
                    .map_err(|e| e.to_string())?;
                let previous_capture = Path::new(text(&req["old_manifest"])?)
                    .parent()
                    .ok_or("PARENT_CAPTURE_DIRECTORY")?
                    .canonicalize()
                    .map_err(|e| e.to_string())?;
                need(
                    !parent.starts_with(previous_state) && !parent.starts_with(previous_capture),
                    "DESTINATION_INSIDE_PARENT_OR_CAPTURE",
                )?;
            }
            let name = destination
                .file_name()
                .and_then(|s| s.to_str())
                .ok_or("DESTINATION_NAME")?;
            let destination = parent.join(name);
            let output_lock_path = parent.join(format!(".{name}.source-advance.lock"));
            if output_lock_path.exists() {
                regular(&output_lock_path)?;
            }
            let output_lock = OpenOptions::new()
                .create(true)
                .truncate(false)
                .read(true)
                .write(true)
                .open(output_lock_path)
                .map_err(|e| e.to_string())?;
            output_lock
                .try_lock_exclusive()
                .map_err(|_| "DESTINATION_WRITER_CONFLICT".to_string())?;
            need(!destination.exists(), "DESTINATION_EXISTS")?;

            let mut old = None;
            let mut old_lock = None;
            let mut old_root = None;
            let mut entries: Vec<Value> = Vec::new();
            let mut parent_anchor = Value::Null;
            let mut old_body = Value::Null;
            let mut work = Work::default();
            let mut candidate_prefix_bytes = 0;
            let mut previous = nat(&candidate.cap.m["anchor"]["slot"])?;
            let mut previous_hash = text(&candidate.cap.m["anchor"]["blockhash"])?.to_string();
            let mut reproject = false;
            let mut evidence_changed = false;
            if mode == "init" {
                need(
                    req["old_manifest"].is_null()
                        && req["old_state"].is_null()
                        && req["old_checkpoint_sha256"].is_null(),
                    "INIT_HAS_PARENT",
                )?;
            } else {
                let path = Path::new(text(&req["old_manifest"])?);
                let b = bundle(path, &policy)?;
                let state_path = Path::new(text(&req["old_state"])?);
                need(
                    !fs::symlink_metadata(state_path)
                        .map_err(|e| e.to_string())?
                        .file_type()
                        .is_symlink(),
                    "SYMLINK_PARENT_STATE",
                )?;
                let root = state_path.canonicalize().map_err(|e| e.to_string())?;
                need(
                    !parent.starts_with(&root) && !parent.starts_with(&b.cap.root),
                    "DESTINATION_INSIDE_PARENT_OR_CAPTURE",
                )?;
                regular(&root.join("writer.lock"))?;
                let lock = OpenOptions::new()
                    .read(true)
                    .write(true)
                    .open(root.join("writer.lock"))
                    .map_err(|e| e.to_string())?;
                lock.try_lock_exclusive()
                    .map_err(|_| "PARENT_WRITER_CONFLICT".to_string())?;
                old_lock = Some(lock);
                let cp_raw = small(&root.join("checkpoint.json"), 2 * 1024 * 1024)?;
                need(
                    hash(&cp_raw) == text(&req["old_checkpoint_sha256"])?,
                    "PARENT_CHECKPOINT_ANCHOR_MISMATCH",
                )?;
                let cp = v0::strict(&cp_raw)?;
                let body = &cp["body"];
                need(
                    cp["body_sha256"] == hash(&bytes(body))
                        && body["schema"] == "sof-runtime.source-checkpoint.v0",
                    "PARENT_CHECKPOINT_FRAME",
                )?;
                need(
                    body["execution_identity"] == execution,
                    "EXECUTION_IDENTITY_MISMATCH",
                )?;
                need(
                    body["source_identity"] == b.source
                        && body["capture_manifest_sha256"] == b.cap.sha
                        && nat(&body["start_slot"])? == b.cap.start,
                    "PARENT_SOURCE_BINDING",
                )?;
                entries = arr(&body["committed"])?.clone();
                need(
                    nat(&body["next_index"])? == entries.len() as u64
                        && entries.len() as u64 == b.cap.end - b.cap.start + 1,
                    "PARENT_CHECKPOINT_NOT_COMPLETE",
                )?;
                let transition = small(&root.join("transition.json"), 2 * 1024 * 1024)?;
                need(
                    hash(&transition) == body["transition_sha256"],
                    "PARENT_TRANSITION_BINDING",
                )?;
                let mut allowed: BTreeSet<String> = [
                    "writer.lock",
                    "checkpoint.json",
                    "transition.json",
                    "projection.jsonl",
                ]
                .iter()
                .map(|s| s.to_string())
                .collect();
                allowed.extend(entries.iter().map(|e| format!("slot-{}.jsonl", e["slot"])));
                let mut actual = BTreeSet::new();
                for item in fs::read_dir(&root).map_err(|e| e.to_string())? {
                    let item = item.map_err(|e| e.to_string())?;
                    regular(&item.path())?;
                    actual.insert(item.file_name().to_string_lossy().to_string());
                }
                need(actual == allowed, "PARENT_STATE_INVENTORY")?;
                let (mut p, mut ph) = (
                    nat(&b.cap.m["anchor"]["slot"])?,
                    text(&b.cap.m["anchor"]["blockhash"])?.to_string(),
                );
                for (i, e) in entries.iter().enumerate() {
                    let s = nat(&e["slot"])?;
                    need(s == b.cap.start + i as u64, "PARENT_CHECKPOINT_ORDER")?;
                    continuity(&b.cap, e, &mut p, &mut ph)?;
                    work.prefix_input_bytes += b.cap.verify_input(s)?;
                    let (digest, size, lines) = digest_file(&segment(&root, s))?;
                    need(
                        digest == e["sha256"]
                            && size == nat(&e["bytes"])?
                            && lines == nat(&e["records"])?,
                        "PARENT_SEGMENT_CORRUPTION",
                    )?;
                    work.prefix_segment_bytes += size;
                }
                let (digest, size, _) = digest_file(&root.join("projection.jsonl"))?;
                need(
                    digest == body["projection_sha256"] && size == nat(&body["projection_bytes"])?,
                    "PARENT_AGGREGATE_CORRUPTION",
                )?;
                parent_anchor = json!(hash(&cp_raw));
                result["affected_checkpoint_sha256"] = parent_anchor.clone();
                result["source_transition"]["from"] = b.source.clone();
                need(
                    candidate.cap.start == b.cap.start && candidate.cap.end >= b.cap.end,
                    "CANDIDATE_RANGE_DOES_NOT_COVER_CHECKPOINT",
                )?;
                need(
                    candidate.cap.m["anchor"] == b.cap.m["anchor"],
                    "CAPTURE_ANCHOR_CONTINUITY_UNCONFIRMED",
                )?;
                for e in &entries {
                    let s = nat(&e["slot"])?;
                    candidate_prefix_bytes += candidate.cap.verify_input(s)?;
                    evidence_changed |= e["input_sha256"] != candidate.cap.source_hash(s);
                    if let Some(block) = candidate.cap.blocks.get(&s) {
                        evidence_changed |= e["header"]["blockhash"] != block["blockhash"];
                    }
                }
                let source_changed = b.source != candidate.source;
                result["source_transition"]["credential_changed"] = json!(source_changed);
                result["source_transition"]["prefix_evidence_changed"] = json!(evidence_changed);
                reproject = source_changed || evidence_changed || mode == "reapprove";
                let mut new_prefix = Vec::new();
                for e in &entries {
                    let s = nat(&e["slot"])?;
                    let new_entry = if reproject {
                        let (_, ne) = project(&candidate.cap, s, true, false, &mut work)?;
                        continuity(&candidate.cap, &ne, &mut previous, &mut previous_hash)?;
                        ne
                    } else {
                        let mut ne = e.clone();
                        ne["input_sha256"] = candidate.cap.source_hash(s);
                        continuity(&candidate.cap, &ne, &mut previous, &mut previous_hash)?;
                        ne
                    };
                    if new_entry["sha256"] != e["sha256"]
                        || new_entry["bytes"] != e["bytes"]
                        || new_entry["records"] != e["records"]
                    {
                        result["status"] = json!("REJECTED_PREFIX_CONFLICT");
                        result["earliest_conflict_slot"] = json!(s);
                        result["compatibility"] = json!("INCOMPATIBLE_WITH_PROPOSED_CAPTURE");
                        result["reason"] = json!("COMMITTED_PREFIX_DIVERGENCE");
                        result["conflict"] = json!({"kind":if e["input_sha256"].is_null() != new_entry["input_sha256"].is_null() {"LISTED_STATUS"} else {"CANONICAL_RECORDS"},
                            "old_segment_sha256":e["sha256"],"candidate_segment_sha256":new_entry["sha256"]});
                        result["work"] = work_report(&work, candidate_prefix_bytes);
                        return Ok(());
                    }
                    new_prefix.push(new_entry);
                }
                entries = new_prefix;
                result["work"] = work_report(&work, candidate_prefix_bytes);
                if source_changed || evidence_changed {
                    need(
                        mode == "reapprove",
                        "SOURCE_OR_PREFIX_EVIDENCE_REAPPROVAL_REQUIRED",
                    )?;
                }
                if mode == "reapprove" {
                    let pair = json!([b.credential_sha, candidate.credential_sha]);
                    need(
                        arr(&policy["reapproval_pairs"])?.contains(&pair),
                        "SOURCE_REAPPROVAL_PAIR_NOT_ALLOWED",
                    )?;
                }
                old_body = body.clone();
                old_root = Some(root);
                old = Some(b);
            }

            let inherited = entries.len();
            let unique = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map_err(|e| e.to_string())?
                .as_nanos();
            let stage_root =
                parent.join(format!(".{name}.staging-{}-{unique}", std::process::id()));
            fs::create_dir(&stage_root).map_err(|e| e.to_string())?;
            let mut stage = Stage {
                root: stage_root,
                published: false,
            };
            if let Some(root) = &old_root {
                for e in &entries {
                    let s = nat(&e["slot"])?;
                    let raw = fs::read(segment(root, s)).map_err(|e| e.to_string())?;
                    need(
                        hash(&raw) == e["sha256"] && raw.len() as u64 == nat(&e["bytes"])?,
                        "PARENT_SEGMENT_CHANGED_DURING_COPY",
                    )?;
                    write_new(&segment(&stage.root, s), &raw)?;
                }
            }
            for s in candidate.cap.start + inherited as u64..=candidate.cap.end {
                let (raw, e) = project(&candidate.cap, s, false, false, &mut work)?;
                result["work"] = work_report(&work, candidate_prefix_bytes);
                continuity(&candidate.cap, &e, &mut previous, &mut previous_hash)?;
                write_new(&segment(&stage.root, s), &raw)?;
                entries.push(e);
                work.newly_committed_slots += 1;
            }
            let mut projection = OpenOptions::new()
                .create_new(true)
                .write(true)
                .open(stage.root.join("projection.jsonl"))
                .map_err(|e| e.to_string())?;
            let mut all = Sha256::new();
            let mut total = 0;
            let mut buffer = [0u8; 65536];
            for e in &entries {
                let mut file = File::open(segment(&stage.root, nat(&e["slot"])?))
                    .map_err(|e| e.to_string())?;
                let mut one = Sha256::new();
                let mut size = 0;
                loop {
                    let n = file.read(&mut buffer).map_err(|e| e.to_string())?;
                    if n == 0 {
                        break;
                    }
                    projection
                        .write_all(&buffer[..n])
                        .map_err(|e| e.to_string())?;
                    one.update(&buffer[..n]);
                    all.update(&buffer[..n]);
                    size += n as u64;
                }
                need(
                    format!("{:x}", one.finalize()) == e["sha256"] && size == nat(&e["bytes"])?,
                    "STAGED_SEGMENT_CORRUPTION",
                )?;
                total += size;
            }
            projection.sync_all().map_err(|e| e.to_string())?;
            drop(projection);
            let projection_hash = format!("{:x}", all.finalize());
            work.aggregate_bytes = total;
            work.post_input_bytes += stable(&candidate, candidate_path)?;
            if let Some(b) = &old {
                work.post_input_bytes += stable(b, Path::new(text(&req["old_manifest"])?))?;
                let root = old_root.as_ref().unwrap();
                need(
                    digest_file(&root.join("checkpoint.json"))?.0 == parent_anchor,
                    "PARENT_CHECKPOINT_CHANGED",
                )?;
                need(
                    digest_file(&root.join("projection.jsonl"))?.0 == old_body["projection_sha256"],
                    "PARENT_AGGREGATE_CHANGED",
                )?;
            }
            need(
                digest_file(policy_path)?.0 == policy_sha
                    && digest_file(request_path)?.0 == hash(&request_raw),
                "REQUEST_OR_POLICY_CHANGED",
            )?;
            let compatibility = if mode == "init" {
                "INITIALIZED"
            } else if reproject {
                "REAPPROVED_EQUAL_RECORDS"
            } else {
                "INHERITED_EXACT_SOURCE_EVIDENCE"
            };
            let transition = json!({"schema":"sof-runtime.source-transition.v0","request_sha256":hash(&request_raw),"mode":mode,
                "policy_sha256":policy_sha,"source_transition":result["source_transition"],"parent_checkpoint_sha256":parent_anchor,
                "candidate_manifest_sha256":candidate.cap.sha,"compatibility":compatibility,"inherited_slots":inherited,
                "new_slots":work.newly_committed_slots,"prefix_reprojection_required":reproject,"work":work_report(&work,candidate_prefix_bytes)});
            let transition_raw = bytes(&transition);
            let body = json!({"schema":"sof-runtime.source-checkpoint.v0","source_identity":candidate.source,"execution_identity":execution,
                "capture_manifest_sha256":candidate.cap.sha,"start_slot":candidate.cap.start,"next_index":entries.len(),"committed":entries,
                "parent_checkpoint_sha256":parent_anchor,"transition_sha256":hash(&transition_raw),
                "projection_sha256":projection_hash,"projection_bytes":total});
            let checkpoint_raw = frame(&body);
            write_new(&stage.root.join("transition.json"), &transition_raw)?;
            write_new(&stage.root.join("checkpoint.json"), &checkpoint_raw)?;
            write_new(&stage.root.join("writer.lock"), b"")?;
            need(!destination.exists(), "DESTINATION_EXISTS")?;
            fs::rename(&stage.root, &destination).map_err(|e| e.to_string())?;
            stage.published = true;
            drop(old_lock);
            result["status"] = json!("COMPLETED_OFFLINE_ADVANCEMENT");
            result["published"] = json!(true);
            result["compatibility"] = json!(compatibility);
            result["reason"] = Value::Null;
            result["new_checkpoint_sha256"] = json!(hash(&checkpoint_raw));
            result["source_identity_sha256"] = json!(hash(&bytes(&candidate.source)));
            result["execution_identity_sha256"] = json!(hash(&bytes(&execution)));
            result["projection_sha256"] = json!(projection_hash);
            result["projection_bytes"] = json!(total);
            result["inherited_slots"] = json!(inherited);
            result["new_slots"] = json!(work.newly_committed_slots);
            result["work"] = work_report(&work, candidate_prefix_bytes);
            Ok(())
        })();
        if let Err(error) = decision {
            result["reason"] = json!(error);
        }
        result
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 3 {
        println!(
            "{}",
            json!({"status":"UNRESOLVED","published":false,"reason":"usage: REQUEST_JSON NEW_STATE_DIRECTORY"})
        );
        std::process::exit(2);
    }
    let result = frozen::advance(Path::new(&args[1]), Path::new(&args[2]));
    let success = result["status"] == "COMPLETED_OFFLINE_ADVANCEMENT";
    println!("{result}");
    if !success {
        std::process::exit(2);
    }
}
