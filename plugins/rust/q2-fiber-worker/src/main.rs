use num_bigint::BigUint;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::io::Read;
use std::process::ExitCode;

type Outcome<T> = Result<T, String>;
const SCHEMA: &str = "sof-runtime.q2-parallel.v0";
const MAX_INPUT: u64 = 16 * 1024 * 1024;
const MAX_VALUE: usize = 1_000_000;

fn canonical<T: Serialize>(value: &T) -> Vec<u8> {
    serde_json::to_vec(&serde_json::to_value(value).expect("serializable value"))
        .expect("JSON bytes")
}
fn digest<T: Serialize>(value: &T) -> String {
    format!("{:x}", Sha256::digest(canonical(value)))
}
fn array(value: &Value) -> Outcome<&Vec<Value>> {
    value.as_array().ok_or("array expected".into())
}
fn index(value: &Value) -> Outcome<usize> {
    value
        .as_u64()
        .map(|v| v as usize)
        .ok_or("index expected".into())
}
fn text(value: &Value) -> Outcome<&str> {
    value.as_str().ok_or("string expected".into())
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
struct Typed {
    #[serde(rename = "type")]
    typ: Value,
    value: Value,
}
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Node {
    kind: String,
    #[serde(rename = "type")]
    typ: Value,
    data: Value,
    children: Vec<Node>,
}
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Env {
    defect: Vec<usize>,
    ports: Vec<usize>,
    atom_count: usize,
}
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Report {
    label: String,
    expr: Node,
}
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Command {
    label: String,
    letter: String,
    guard: Node,
}
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Program {
    q: Node,
    reports: Vec<Report>,
    commands: Vec<Command>,
}
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct State {
    state_id: usize,
    causal: BTreeMap<String, Typed>,
}
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Input {
    schema: String,
    binding: Value,
    plan_id: String,
    shard_id: String,
    environment: Env,
    program: Program,
    states: Vec<State>,
    max_steps: u64,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Task {
    input: Input,
    input_sha256: String,
}

struct Budget {
    remaining: u64,
}
impl Budget {
    fn tick(&mut self) -> Outcome<()> {
        self.remaining = self.remaining.checked_sub(1).ok_or("worker step limit")?;
        Ok(())
    }
}

fn record_names(typ: &Value) -> Outcome<&'static [&'static str]> {
    match typ.as_str() {
        Some("Origin") => Ok(&["label", "parents", "target"]),
        Some("AbsRecord") => Ok(&[
            "carrier_at",
            "carrier",
            "partner_at",
            "partner",
            "target",
            "merged",
            "label",
        ]),
        _ => Err("record type expected".into()),
    }
}
fn nat(value: &Typed) -> Outcome<BigUint> {
    let raw = text(&value.value)?;
    if value.typ != "Nat" || raw.len() > 4096 {
        return Err("Nat type/digit bound".into());
    }
    BigUint::parse_bytes(raw.as_bytes(), 10).ok_or("invalid Nat".into())
}
fn nat_json(value: BigUint) -> Outcome<Value> {
    let raw = value.to_str_radix(10);
    if raw.len() > 4096 {
        return Err("Nat result digit limit".into());
    }
    Ok(json!(raw))
}
fn boolean(value: &Typed) -> Outcome<bool> {
    if value.typ != "Bool" {
        return Err("Bool expected".into());
    }
    value.value.as_bool().ok_or("Bool payload expected".into())
}
fn block(value: &Value) -> Outcome<BTreeSet<usize>> {
    array(value)?.iter().map(index).collect()
}
fn option_some(value: Value) -> Value {
    json!({"some":value})
}

fn operation(node: &Node, args: &[Typed], env: &Env) -> Outcome<Value> {
    let op = text(&node.data[0])?;
    let a = |i: usize| {
        args.get(i)
            .ok_or_else(|| "missing operation argument".to_string())
    };
    Ok(match op {
        "eq" => json!(a(0)? == a(1)?),
        "not" => json!(!boolean(a(0)?)?),
        "and" => json!(boolean(a(0)?)? && boolean(a(1)?)?),
        "or" => json!(boolean(a(0)?)? || boolean(a(1)?)?),
        "add" => nat_json(nat(a(0)?)? + nat(a(1)?)?)?,
        "lt" => json!(nat(a(0)?)? < nat(a(1)?)?),
        "le" => json!(nat(a(0)?)? <= nat(a(1)?)?),
        "mod" => {
            let modulus = BigUint::parse_bytes(text(&node.data[1])?.as_bytes(), 10)
                .ok_or("invalid modulus")?;
            if modulus == BigUint::from(0u8) {
                return Err("zero modulus".into());
            }
            nat_json(nat(a(0)?)? % modulus)?
        }
        "union" => json!(
            block(&a(0)?.value)?
                .union(&block(&a(1)?.value)?)
                .copied()
                .collect::<Vec<_>>()
        ),
        "intersection" => json!(
            block(&a(0)?.value)?
                .intersection(&block(&a(1)?.value)?)
                .copied()
                .collect::<Vec<_>>()
        ),
        "subset" => json!(block(&a(0)?.value)?.is_subset(&block(&a(1)?.value)?)),
        "cardinality" => json!(block(&a(0)?.value)?.len().to_string()),
        "cons" => {
            let mut items = vec![a(0)?.value.clone()];
            items.extend(array(&a(1)?.value)?.clone());
            json!(items)
        }
        "entries" => a(0)?.value.clone(),
        "lookup" => {
            let mut found = Value::Null;
            for entry in array(&a(0)?.value)? {
                if entry[0] == a(1)?.value {
                    found = option_some(entry[1].clone());
                    break;
                }
            }
            found
        }
        "carrier" => {
            let selected = block(&a(1)?.value)?;
            let matches = array(&a(0)?.value)?
                .iter()
                .filter_map(|entry| match block(&entry[1]) {
                    Ok(atoms) if selected.is_subset(&atoms) => Some(Ok(entry.clone())),
                    Ok(_) => None,
                    Err(error) => Some(Err(error)),
                })
                .collect::<Outcome<Vec<_>>>()?;
            if matches.len() == 1 {
                option_some(matches[0].clone())
            } else {
                Value::Null
            }
        }
        "f_p" | "f_d" => {
            let q = index(&a(0)?.value)?;
            if q >= env.defect.len() {
                return Err("position outside environment".into());
            }
            json!(if op == "f_p" {
                (q + 1) % env.defect.len()
            } else {
                env.defect[q]
            })
        }
        _ => return Err("unsupported compiled primitive".into()),
    })
}

fn evaluate(
    node: &Node,
    query: &BTreeMap<String, Typed>,
    env: &Env,
    budget: &mut Budget,
    variables: &BTreeMap<String, Typed>,
    depth: usize,
) -> Outcome<Typed> {
    budget.tick()?;
    if depth > 100 {
        return Err("worker expression depth limit".into());
    }
    let child = |i: usize| {
        node.children
            .get(i)
            .ok_or_else(|| "missing expression child".to_string())
    };
    let eval = |expr: &Node, budget: &mut Budget, vars: &BTreeMap<String, Typed>| {
        evaluate(expr, query, env, budget, vars, depth + 1)
    };
    let result = match node.kind.as_str() {
        "literal" => Typed {
            typ: node.typ.clone(),
            value: node.data.clone(),
        },
        "query" => query.get(text(&node.data)?).ok_or("unknown query")?.clone(),
        "var" => variables
            .get(text(&node.data)?)
            .ok_or("unbound variable")?
            .clone(),
        "if" => {
            let condition = eval(child(0)?, budget, variables)?;
            eval(
                child(if boolean(&condition)? { 1 } else { 2 })?,
                budget,
                variables,
            )?
        }
        "case" => {
            let value = eval(child(0)?, budget, variables)?;
            if value.value.is_null() {
                eval(child(1)?, budget, variables)?
            } else {
                let mut scope = variables.clone();
                scope.insert(
                    text(&node.data)?.to_owned(),
                    Typed {
                        typ: value.typ[1].clone(),
                        value: value.value["some"].clone(),
                    },
                );
                eval(child(2)?, budget, &scope)?
            }
        }
        "fold" => {
            let items = eval(child(0)?, budget, variables)?;
            let mut acc = eval(child(1)?, budget, variables)?;
            for item in array(&items.value)? {
                budget.tick()?;
                let mut scope = variables.clone();
                scope.insert(text(&node.data[0])?.to_owned(), acc);
                scope.insert(
                    text(&node.data[1])?.to_owned(),
                    Typed {
                        typ: items.typ[1].clone(),
                        value: item.clone(),
                    },
                );
                acc = eval(child(2)?, budget, &scope)?;
            }
            acc
        }
        _ => {
            let mut args = Vec::new();
            let mut bytes = 0;
            for expr in &node.children {
                let value = eval(expr, budget, variables)?;
                bytes += canonical(&value).len();
                if bytes > MAX_VALUE {
                    return Err("worker argument size limit".into());
                }
                args.push(value);
            }
            let value = match node.kind.as_str() {
                "fst" => args[0].value[0].clone(),
                "snd" => args[0].value[1].clone(),
                "field" => args[0].value[record_names(&args[0].typ)?[index(&node.data)?]].clone(),
                "pair" | "list" => json!(args.into_iter().map(|x| x.value).collect::<Vec<_>>()),
                "record" => {
                    let mut fields = serde_json::Map::new();
                    for (name, value) in record_names(&node.typ)?.iter().zip(args) {
                        fields.insert((*name).to_owned(), value.value);
                    }
                    Value::Object(fields)
                }
                "some" => option_some(args[0].value.clone()),
                "none" => Value::Null,
                "op" => operation(node, &args, env)?,
                _ => return Err("unsupported compiled constructor".into()),
            };
            Typed {
                typ: node.typ.clone(),
                value,
            }
        }
    };
    if result.typ != node.typ || canonical(&result).len() > MAX_VALUE {
        return Err("worker result type/size limit".into());
    }
    Ok(result)
}

fn successor(
    query: &BTreeMap<String, Typed>,
    env: &Env,
    letter: &str,
) -> Outcome<BTreeMap<String, Typed>> {
    let partition = query.get("CurrentPartition").ok_or("partition missing")?;
    let selected = block(&query.get("SelectedBlock").ok_or("selected missing")?.value)?;
    let mut packets = BTreeMap::new();
    for entry in array(&partition.value)? {
        packets.insert(index(&entry[0])?, block(&entry[1])?);
    }
    let mut moved: BTreeMap<usize, BTreeSet<usize>> = BTreeMap::new();
    for (&q, atoms) in &packets {
        let target = if letter == "p" {
            (q + 1) % env.defect.len()
        } else {
            *env.defect.get(q).ok_or("bad position")?
        };
        moved.entry(target).or_default().extend(atoms);
    }
    let mut result = query.clone();
    result.get_mut("CurrentPartition").unwrap().value =
        json!(moved.iter().map(|(q, b)| json!([q, b])).collect::<Vec<_>>());
    if letter == "d" {
        let k0 = env.ports[0];
        let k1 = env.ports[1];
        if let (Some(left), Some(right)) = (packets.get(&k0), packets.get(&k1)) {
            let carrier = if selected.is_subset(left) {
                Some((k0, left, k1, right))
            } else if selected.is_subset(right) {
                Some((k1, right, k0, left))
            } else {
                None
            };
            if let Some((q, c, s, b)) = carrier {
                let merged = c.union(b).copied().collect::<BTreeSet<_>>();
                let record = json!({"carrier_at":q,"carrier":c,"partner_at":s,"partner":b,
                                    "target":env.defect[k0],"merged":merged,"label":"d"});
                result
                    .get_mut("AbsorptionSequence")
                    .ok_or("absorption missing")?
                    .value
                    .as_array_mut()
                    .ok_or("absorption array")?
                    .push(record);
            }
        }
    }
    Ok(result)
}

#[derive(Clone, Serialize)]
struct Signature {
    reports: Vec<Value>,
    enabled: Vec<String>,
    successor_q: BTreeMap<String, Typed>,
}
#[derive(Serialize)]
struct FiberRecord {
    q_key: Typed,
    signature: Signature,
    members: Vec<usize>,
    witness_state_id: usize,
}

fn run(task: Task) -> Outcome<Value> {
    let input = task.input;
    if input.schema != format!("{SCHEMA}.task")
        || digest(&input) != task.input_sha256
        || input.binding["versions"]["worker"] != "Q2_FIBER_WORKER_V0"
        || input.binding["versions"]["encoding"] != "Q2_INDEXED_TYPED_VALUES_V0"
        || input.binding["versions"]["ir"] != "Q2_COMPILED_IR_V0"
    {
        return Err("task/version/hash mismatch".into());
    }
    let env = &input.environment;
    if !(2..=4).contains(&env.defect.len())
        || env.ports.len() != 2
        || env.ports[0] == env.ports[1]
        || env.ports.iter().any(|q| *q >= env.defect.len())
        || input.max_steps == 0
    {
        return Err("unsupported environment/limits".into());
    }
    let mut budget = Budget {
        remaining: input.max_steps,
    };
    let vars = BTreeMap::new();
    let mut groups: BTreeMap<(String, String), FiberRecord> = BTreeMap::new();
    let mut covered = BTreeSet::new();
    for state in &input.states {
        if !covered.insert(state.state_id) {
            return Err("duplicate state ID".into());
        }
        let eval = |expr: &Node, queries: &BTreeMap<String, Typed>, budget: &mut Budget| {
            evaluate(expr, queries, env, budget, &vars, 0)
        };
        let q = eval(&input.program.q, &state.causal, &mut budget)?;
        let mut reports = Vec::new();
        for report in &input.program.reports {
            reports.push(
                json!({"label":report.label,"value":eval(&report.expr,&state.causal,&mut budget)?}),
            );
        }
        let mut enabled = Vec::new();
        let mut successor_q = BTreeMap::new();
        for command in &input.program.commands {
            if boolean(&eval(&command.guard, &state.causal, &mut budget)?)? {
                enabled.push(command.label.clone());
                let next = successor(&state.causal, env, &command.letter)?;
                successor_q.insert(
                    command.label.clone(),
                    eval(&input.program.q, &next, &mut budget)?,
                );
            }
        }
        let signature = Signature {
            reports,
            enabled,
            successor_q,
        };
        let key = (
            String::from_utf8(canonical(&q)).unwrap(),
            String::from_utf8(canonical(&signature)).unwrap(),
        );
        groups
            .entry(key)
            .or_insert_with(|| FiberRecord {
                q_key: q,
                signature,
                members: Vec::new(),
                witness_state_id: state.state_id,
            })
            .members
            .push(state.state_id);
    }
    let mut by_q: BTreeMap<String, Vec<usize>> = BTreeMap::new();
    for ((q, _), record) in &mut groups {
        record.members.sort_unstable();
        record.witness_state_id = record.members[0];
        by_q.entry(q.clone())
            .or_default()
            .push(record.witness_state_id);
    }
    let local_conflicts = by_q
        .values_mut()
        .filter_map(|ids| {
            ids.sort_unstable();
            if ids.len() > 1 {
                Some(json!({"left":ids[0],"right":ids[1]}))
            } else {
                None
            }
        })
        .collect::<Vec<_>>();
    let covered = covered.into_iter().collect::<Vec<_>>();
    Ok(
        json!({"schema":format!("{SCHEMA}.shard"),"status":"COMPLETE","binding":input.binding,
        "plan_id":input.plan_id,"shard_id":input.shard_id,"task_input_sha256":task.input_sha256,
        "coverage_digest":digest(&covered),"fiber_records":groups.into_values().collect::<Vec<_>>(),
        "local_conflicts":local_conflicts,"evaluation_steps":input.max_steps-budget.remaining}),
    )
}

fn main() -> ExitCode {
    let result = (|| -> Outcome<Value> {
        let args = std::env::args().skip(1).collect::<Vec<_>>();
        if args.len() != 1 {
            return Err("usage: q2-fiber-worker TASK.json".into());
        }
        let mut bytes = Vec::new();
        std::fs::File::open(&args[0])
            .map_err(|e| e.to_string())?
            .take(MAX_INPUT + 1)
            .read_to_end(&mut bytes)
            .map_err(|e| e.to_string())?;
        if bytes.len() as u64 > MAX_INPUT {
            return Err("worker input size limit".into());
        }
        run(serde_json::from_slice(&bytes).map_err(|e| e.to_string())?)
    })();
    match result {
        Ok(value) => {
            println!("{value}");
            ExitCode::SUCCESS
        }
        Err(detail) => {
            println!(
                "{}",
                json!({"schema":format!("{SCHEMA}.shard"),"status":"UNRESOLVED","detail":detail})
            );
            ExitCode::from(2)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn exact_nat_arithmetic_does_not_identify_types_or_wrap() {
        let value = Typed {
            typ: json!("Nat"),
            value: json!("340282366920938463463374607431768211456"),
        };
        let env = Env {
            defect: vec![0, 0],
            ports: vec![0, 1],
            atom_count: 2,
        };
        let node = Node {
            kind: "op".into(),
            typ: json!("Nat"),
            data: json!(["add", null]),
            children: vec![],
        };
        assert_eq!(
            operation(&node, &[value.clone(), value], &env).unwrap(),
            json!("680564733841876926926749214863536422912")
        );
        assert!(
            nat(&Typed {
                typ: json!("Pos"),
                value: json!("1")
            })
            .is_err()
        );
        assert!(
            boolean(&Typed {
                typ: json!("Nat"),
                value: json!("1")
            })
            .is_err()
        );
    }

    #[test]
    fn source_relative_port_order_and_unrelated_fusion_are_kept() {
        let query = BTreeMap::from([
            (
                "CurrentPartition".into(),
                Typed {
                    typ: json!("Partition"),
                    value: json!([[0, [2]], [1, [3]], [3, [0, 1]]]),
                },
            ),
            (
                "SelectedBlock".into(),
                Typed {
                    typ: json!("Block"),
                    value: json!([0, 1]),
                },
            ),
            (
                "OriginSnapshot".into(),
                Typed {
                    typ: json!("Origin"),
                    value: json!({"label":"d","parents":[[1,[1]],[0,[0]]],"target":0}),
                },
            ),
            (
                "AbsorptionSequence".into(),
                Typed {
                    typ: json!(["List", "AbsRecord"]),
                    value: json!([]),
                },
            ),
        ]);
        let env = Env {
            defect: vec![0, 0, 1, 2],
            ports: vec![1, 0],
            atom_count: 4,
        };
        let next = successor(&query, &env, "d").unwrap();
        assert_eq!(
            next["CurrentPartition"].value,
            json!([[0, [2, 3]], [2, [0, 1]]])
        );
        assert_eq!(next["AbsorptionSequence"].value, json!([]));
        assert_eq!(next["OriginSnapshot"], query["OriginSnapshot"]);
    }
}
