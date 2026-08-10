use serde::de::{self, Deserialize, Deserializer, MapAccess, SeqAccess, Visitor};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet, VecDeque};
use std::env;
use std::fmt;
use std::io::{self, Read, Write};
use std::process::ExitCode;
use unicode_normalization::UnicodeNormalization;

const PLUGIN_ID: &str = "org.rime.positive-word-support";
const PLUGIN_VERSION: &str = "0.1.0";

#[derive(Clone, Debug, PartialEq, Eq)]
enum CanonicalValue {
    Null,
    Bool(bool),
    Integer(i64),
    String(String),
    Array(Vec<CanonicalValue>),
    Object(BTreeMap<String, CanonicalValue>),
}

impl<'de> Deserialize<'de> for CanonicalValue {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        deserializer.deserialize_any(CanonicalVisitor)
    }
}

struct CanonicalVisitor;

impl<'de> Visitor<'de> for CanonicalVisitor {
    type Value = CanonicalValue;

    fn expecting(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("a sof-cjson-v1 value")
    }

    fn visit_unit<E>(self) -> Result<Self::Value, E> {
        Ok(CanonicalValue::Null)
    }

    fn visit_none<E>(self) -> Result<Self::Value, E> {
        Ok(CanonicalValue::Null)
    }

    fn visit_bool<E>(self, value: bool) -> Result<Self::Value, E> {
        Ok(CanonicalValue::Bool(value))
    }

    fn visit_i64<E>(self, value: i64) -> Result<Self::Value, E> {
        Ok(CanonicalValue::Integer(value))
    }

    fn visit_u64<E>(self, value: u64) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        let value = i64::try_from(value)
            .map_err(|_| E::custom("integer is outside the signed 64-bit canonical range"))?;
        Ok(CanonicalValue::Integer(value))
    }

    fn visit_f64<E>(self, _value: f64) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        Err(E::custom(
            "binary floating-point values are forbidden by sof-cjson-v1",
        ))
    }

    fn visit_str<E>(self, value: &str) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        validate_nfc(value).map_err(E::custom)?;
        Ok(CanonicalValue::String(value.to_owned()))
    }

    fn visit_string<E>(self, value: String) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        validate_nfc(&value).map_err(E::custom)?;
        Ok(CanonicalValue::String(value))
    }

    fn visit_seq<A>(self, mut sequence: A) -> Result<Self::Value, A::Error>
    where
        A: SeqAccess<'de>,
    {
        let mut values = Vec::new();
        while let Some(value) = sequence.next_element()? {
            values.push(value);
        }
        Ok(CanonicalValue::Array(values))
    }

    fn visit_map<A>(self, mut map: A) -> Result<Self::Value, A::Error>
    where
        A: MapAccess<'de>,
    {
        let mut values = BTreeMap::new();
        while let Some(key) = map.next_key::<String>()? {
            validate_nfc(&key).map_err(de::Error::custom)?;
            if values.contains_key(&key) {
                return Err(de::Error::custom(format!(
                    "duplicate JSON object key: {key}"
                )));
            }
            values.insert(key, map.next_value()?);
        }
        Ok(CanonicalValue::Object(values))
    }
}

fn validate_nfc(value: &str) -> Result<(), String> {
    if value.nfc().eq(value.chars()) {
        Ok(())
    } else {
        Err("string is not Unicode NFC".to_owned())
    }
}

fn reject_integer_negative_zero(input: &str) -> Result<(), String> {
    let bytes = input.as_bytes();
    let mut index = 0;
    let mut in_string = false;
    let mut escaped = false;
    while index < bytes.len() {
        let byte = bytes[index];
        if in_string {
            if escaped {
                escaped = false;
            } else if byte == b'\\' {
                escaped = true;
            } else if byte == b'"' {
                in_string = false;
            }
            index += 1;
            continue;
        }
        if byte == b'"' {
            in_string = true;
            index += 1;
            continue;
        }
        if byte == b'-' && bytes.get(index + 1) == Some(&b'0') {
            let terminator = bytes.get(index + 2).copied();
            if terminator
                .is_none_or(|next| next.is_ascii_whitespace() || matches!(next, b',' | b']' | b'}'))
            {
                return Err("negative-zero JSON integer is forbidden".to_owned());
            }
        }
        index += 1;
    }
    Ok(())
}

fn parse_canonical(input: &str) -> Result<CanonicalValue, String> {
    reject_integer_negative_zero(input)?;
    let mut deserializer = serde_json::Deserializer::from_str(input);
    let value =
        CanonicalValue::deserialize(&mut deserializer).map_err(|error| error.to_string())?;
    deserializer.end().map_err(|error| error.to_string())?;
    Ok(value)
}

fn canonical_bytes(value: &CanonicalValue) -> Result<Vec<u8>, String> {
    let mut output = Vec::new();
    write_canonical(value, &mut output)?;
    Ok(output)
}

fn write_canonical(value: &CanonicalValue, output: &mut Vec<u8>) -> Result<(), String> {
    match value {
        CanonicalValue::Null => output.extend_from_slice(b"null"),
        CanonicalValue::Bool(true) => output.extend_from_slice(b"true"),
        CanonicalValue::Bool(false) => output.extend_from_slice(b"false"),
        CanonicalValue::Integer(number) => output.extend_from_slice(number.to_string().as_bytes()),
        CanonicalValue::String(text) => output.extend_from_slice(
            serde_json::to_string(text)
                .map_err(|error| error.to_string())?
                .as_bytes(),
        ),
        CanonicalValue::Array(items) => {
            output.push(b'[');
            for (index, item) in items.iter().enumerate() {
                if index > 0 {
                    output.push(b',');
                }
                write_canonical(item, output)?;
            }
            output.push(b']');
        }
        CanonicalValue::Object(items) => {
            output.push(b'{');
            for (index, (key, item)) in items.iter().enumerate() {
                if index > 0 {
                    output.push(b',');
                }
                output.extend_from_slice(
                    serde_json::to_string(key)
                        .map_err(|error| error.to_string())?
                        .as_bytes(),
                );
                output.push(b':');
                write_canonical(item, output)?;
            }
            output.push(b'}');
        }
    }
    Ok(())
}

fn sha256_hex(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

fn text(value: impl Into<String>) -> CanonicalValue {
    CanonicalValue::String(value.into())
}

fn integer(value: usize) -> Result<CanonicalValue, String> {
    Ok(CanonicalValue::Integer(i64::try_from(value).map_err(
        |_| "computed integer exceeds signed 64-bit range",
    )?))
}

fn object<I, K>(entries: I) -> CanonicalValue
where
    I: IntoIterator<Item = (K, CanonicalValue)>,
    K: Into<String>,
{
    CanonicalValue::Object(
        entries
            .into_iter()
            .map(|(key, value)| (key.into(), value))
            .collect(),
    )
}

fn object_ref(value: &CanonicalValue) -> Result<&BTreeMap<String, CanonicalValue>, String> {
    match value {
        CanonicalValue::Object(items) => Ok(items),
        _ => Err("expected JSON object".to_owned()),
    }
}

fn array_ref(value: &CanonicalValue) -> Result<&[CanonicalValue], String> {
    match value {
        CanonicalValue::Array(items) => Ok(items),
        _ => Err("expected JSON array".to_owned()),
    }
}

fn string_ref(value: &CanonicalValue) -> Result<&str, String> {
    match value {
        CanonicalValue::String(text) => Ok(text),
        _ => Err("expected JSON string".to_owned()),
    }
}

fn integer_ref(value: &CanonicalValue) -> Result<i64, String> {
    match value {
        CanonicalValue::Integer(number) => Ok(*number),
        _ => Err("expected JSON integer".to_owned()),
    }
}

fn required<'a>(
    object: &'a BTreeMap<String, CanonicalValue>,
    key: &str,
) -> Result<&'a CanonicalValue, String> {
    object
        .get(key)
        .ok_or_else(|| format!("missing required field: {key}"))
}

fn required_string<'a>(
    object: &'a BTreeMap<String, CanonicalValue>,
    key: &str,
) -> Result<&'a str, String> {
    string_ref(required(object, key)?).map_err(|_| format!("field {key} must be a string"))
}

struct MarkovSource {
    source_id: String,
    states: Vec<String>,
    adjacency: Vec<Vec<bool>>,
}

fn parse_markov_source(value: &CanonicalValue) -> Result<MarkovSource, String> {
    let source = object_ref(value)?;
    if required_string(source, "schema_id")? != "rime.markov.source.v1" {
        return Err("unsupported Markov source schema".to_owned());
    }
    let source_id = required_string(source, "source_id")?.to_owned();
    let states = array_ref(required(source, "states")?)?
        .iter()
        .map(string_ref)
        .collect::<Result<Vec<_>, _>>()?
        .into_iter()
        .map(str::to_owned)
        .collect::<Vec<_>>();
    if states.is_empty() || states.iter().any(String::is_empty) {
        return Err("states must be finite, nonempty, and nonempty-labelled".to_owned());
    }
    if states.iter().collect::<BTreeSet<_>>().len() != states.len() {
        return Err("state labels must be unique".to_owned());
    }
    let rows = array_ref(required(source, "transition_numerators")?)?;
    let denominators = array_ref(required(source, "row_denominators")?)?;
    if rows.len() != states.len() || denominators.len() != states.len() {
        return Err("Markov matrix and denominator census must match the state count".to_owned());
    }
    let mut adjacency = Vec::with_capacity(states.len());
    for (row_index, (row_value, denominator_value)) in
        rows.iter().zip(denominators.iter()).enumerate()
    {
        let row = array_ref(row_value)?;
        if row.len() != states.len() {
            return Err(format!(
                "Markov row {row_index} must contain {} entries",
                states.len()
            ));
        }
        let denominator = integer_ref(denominator_value)?;
        if denominator < 1 {
            return Err("row denominators must be positive".to_owned());
        }
        let numerators = row.iter().map(integer_ref).collect::<Result<Vec<_>, _>>()?;
        if numerators.iter().any(|value| *value < 0) {
            return Err("transition numerators must be nonnegative".to_owned());
        }
        let sum = numerators.iter().try_fold(0_i64, |sum, value| {
            sum.checked_add(*value)
                .ok_or_else(|| "Markov row sum exceeds signed 64-bit range".to_owned())
        })?;
        if sum != denominator {
            return Err(format!(
                "Markov row {row_index} has numerator sum {sum}, expected {denominator}"
            ));
        }
        adjacency.push(numerators.into_iter().map(|value| value > 0).collect());
    }
    Ok(MarkovSource {
        source_id,
        states,
        adjacency,
    })
}

fn expected_policy() -> CanonicalValue {
    object([(
        "positive_word",
        object([
            ("mode", text("exhaustive")),
            ("pair_scope", text("off_diagonal")),
        ]),
    )])
}

fn expected_semantic_environment() -> CanonicalValue {
    object([
        ("algorithm_mode", text("exhaustive_support_bfs")),
        (
            "arithmetic_backend",
            text("exact_nonnegative_rational_support"),
        ),
        ("dependency_lock_digest", CanonicalValue::Null),
        ("feature_flags", CanonicalValue::Array(Vec::new())),
    ])
}

fn validate_request(request: &CanonicalValue) -> Result<(), String> {
    let fields = object_ref(request)?;
    if required_string(fields, "schema_id")? != "sof.run-request.v1" {
        return Err("unsupported RunRequest schema".to_owned());
    }
    if required_string(fields, "carrier_kind")? != "positive_word_support" {
        return Err("unsupported carrier_kind".to_owned());
    }
    let plugin = object_ref(required(fields, "plugin")?)?;
    if required_string(plugin, "plugin_id")? != PLUGIN_ID
        || required_string(plugin, "plugin_version")? != PLUGIN_VERSION
    {
        return Err("plugin identity mismatch".to_owned());
    }
    if required(fields, "policies")? != &expected_policy() {
        return Err("unsupported positive-word policy".to_owned());
    }
    if required(fields, "semantic_environment")? != &expected_semantic_environment() {
        return Err("semantic environment mismatch".to_owned());
    }
    parse_markov_source(required(fields, "source")?)?;
    required_string(fields, "execution_id")?;
    required_string(fields, "created_at")?;
    required_string(fields, "artifact_directory")?;

    let semantic_payload = object([
        ("canonical_json_profile", text("sof-cjson-v1")),
        ("carrier_kind", required(fields, "carrier_kind")?.clone()),
        (
            "contract_versions",
            required(fields, "contract_versions")?.clone(),
        ),
        ("plugin", required(fields, "plugin")?.clone()),
        ("policies", required(fields, "policies")?.clone()),
        (
            "semantic_environment",
            required(fields, "semantic_environment")?.clone(),
        ),
        ("source", required(fields, "source")?.clone()),
    ]);
    let expected = format!(
        "semrun:sha256:{}",
        sha256_hex(&canonical_bytes(&semantic_payload)?)
    );
    if required_string(fields, "semantic_run_id")? != expected {
        return Err("semantic run identity mismatch".to_owned());
    }
    Ok(())
}

fn pair_depths(source: &MarkovSource) -> Result<Vec<CanonicalValue>, String> {
    let size = source.states.len();
    let mut pairs = Vec::with_capacity(size.saturating_mul(size.saturating_sub(1)));
    for start in 0..size {
        let mut distances = vec![None; size];
        distances[start] = Some(0_usize);
        let mut queue = VecDeque::from([start]);
        while let Some(current) = queue.pop_front() {
            let next_depth = distances[current].expect("queued states have a depth") + 1;
            for (target, distance) in distances.iter_mut().enumerate() {
                if source.adjacency[current][target] && distance.is_none() {
                    *distance = Some(next_depth);
                    queue.push_back(target);
                }
            }
        }
        for (target, depth) in distances.into_iter().enumerate() {
            if start == target {
                continue;
            }
            pairs.push(object([
                ("source", text(source.states[start].clone())),
                ("target", text(source.states[target].clone())),
                (
                    "first_positive_depth",
                    match depth {
                        Some(value) => integer(value)?,
                        None => CanonicalValue::Null,
                    },
                ),
            ]));
        }
    }
    Ok(pairs)
}

fn compute_bundle(request: &CanonicalValue) -> Result<CanonicalValue, String> {
    validate_request(request)?;
    let request_fields = object_ref(request)?;
    let source_value = required(request_fields, "source")?;
    let policy_value = required(request_fields, "policies")?;
    let source = parse_markov_source(source_value)?;
    let semantic_run_id = required_string(request_fields, "semantic_run_id")?;
    let execution_id = required_string(request_fields, "execution_id")?;
    let created_at = required_string(request_fields, "created_at")?;
    let pairs = pair_depths(&source)?;
    let finite_depths = pairs
        .iter()
        .filter_map(|pair| {
            object_ref(pair)
                .ok()?
                .get("first_positive_depth")
                .and_then(|value| match value {
                    CanonicalValue::Integer(number) => Some(*number),
                    _ => None,
                })
        })
        .collect::<Vec<_>>();
    let payload_id = "payload.ordered-pair-first-hits";
    let payload = object([
        ("schema_id", text("rime.positive-word-support.finding.v1")),
        ("payload_id", text(payload_id)),
        ("kind", text("ordered_pair_first_hit_census")),
        ("pairs", CanonicalValue::Array(pairs.clone())),
        ("reachable_pair_count", integer(finite_depths.len())?),
        (
            "unreachable_pair_count",
            integer(pairs.len() - finite_depths.len())?,
        ),
        (
            "maximum_first_hit_depth",
            finite_depths
                .iter()
                .max()
                .copied()
                .map(CanonicalValue::Integer)
                .unwrap_or(CanonicalValue::Null),
        ),
        ("closure_exhausted", CanonicalValue::Bool(true)),
    ]);
    let envelope = object([
        ("schema_id", text("sof.finding.v1")),
        (
            "finding_id",
            text(format!(
                "finding:{}:positive-word-support",
                source.source_id
            )),
        ),
        ("record_kind", text("strict_sof")),
        ("source_ref", text(format!("source:{}", source.source_id))),
        ("carrier_ref", text("extension:positive-word-support:v1")),
        (
            "scope",
            object([
                (
                    "object_ids",
                    CanonicalValue::Array(vec![text(format!(
                        "positive-word-support:{}",
                        source.source_id
                    ))]),
                ),
                (
                    "pair_scope",
                    object([("kind", text("ordered_off_diagonal"))]),
                ),
                (
                    "depth_scope",
                    object([
                        ("kind", text("exact_positive_power")),
                        ("starts_at", CanonicalValue::Integer(1)),
                    ]),
                ),
            ]),
        ),
        ("result_state", text("OBSERVED")),
        ("claim_status", text("Computational Observation")),
        ("value_ref", text(payload_id)),
        (
            "policy_refs",
            CanonicalValue::Array(vec![text("policy:positive-word-orbit-exhaustion")]),
        ),
        ("evidence_refs", CanonicalValue::Array(Vec::new())),
        ("derivation_refs", CanonicalValue::Array(Vec::new())),
        (
            "provenance",
            object([
                ("producer", text(PLUGIN_ID)),
                ("producer_version", text(PLUGIN_VERSION)),
                ("semantic_run_id", text(semantic_run_id)),
                ("execution_id", text(execution_id)),
                ("created_at", text(created_at)),
            ]),
        ),
    ]);
    Ok(object([
        ("schema_id", text("rime.positive-word-support.bundle.v1")),
        ("semantic_run_id", text(semantic_run_id)),
        ("execution_id", text(execution_id)),
        (
            "source_digest",
            text(sha256_hex(&canonical_bytes(source_value)?)),
        ),
        (
            "policy_digest",
            text(sha256_hex(&canonical_bytes(policy_value)?)),
        ),
        (
            "object",
            object([
                ("schema_id", text("rime.positive-word-support.object.v1")),
                (
                    "object_id",
                    text(format!("positive-word-support:{}", source.source_id)),
                ),
                ("source_ref", text(format!("source:{}", source.source_id))),
                ("state_count", integer(source.states.len())?),
                ("operator_label", text("P")),
                ("pair_scope", text("ordered_off_diagonal")),
                (
                    "semantics",
                    text("first positive power with nonzero coordinate-sector support"),
                ),
            ]),
        ),
        (
            "findings",
            CanonicalValue::Array(vec![object([("envelope", envelope), ("payload", payload)])]),
        ),
        (
            "claim_boundary",
            text(
                "Single-letter nonnegative support first hits are not mixing times, route depth, rank collapse, or Lie/Hall depth.",
            ),
        ),
    ]))
}

fn read_stdin() -> Result<String, String> {
    let mut input = String::new();
    io::stdin()
        .read_to_string(&mut input)
        .map_err(|error| format!("failed to read stdin as UTF-8: {error}"))?;
    Ok(input)
}

fn run() -> Result<(), String> {
    let mode = env::args().nth(1);
    if mode.as_deref() == Some("--fail") {
        eprintln!("sof-rust-positive-word: deterministic failure fixture");
        return Err("__FIXED_FAILURE__".to_owned());
    }
    let input = read_stdin()?;
    let parsed = parse_canonical(&input)?;
    let output = match mode.as_deref() {
        None => canonical_bytes(&compute_bundle(&parsed)?)?,
        Some("--canonicalize") => canonical_bytes(&parsed)?,
        Some("--canonical-sha256") => sha256_hex(&canonical_bytes(&parsed)?).into_bytes(),
        Some(other) => return Err(format!("unknown argument: {other}")),
    };
    io::stdout()
        .write_all(&output)
        .map_err(|error| format!("failed to write stdout: {error}"))?;
    Ok(())
}

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) if error == "__FIXED_FAILURE__" => ExitCode::from(17),
        Err(error) => {
            eprintln!("sof-rust-positive-word: {error}");
            ExitCode::from(2)
        }
    }
}
