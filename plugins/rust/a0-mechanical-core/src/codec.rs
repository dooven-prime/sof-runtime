use crate::{Error, Result};
use serde::de::{self, MapAccess, SeqAccess, Visitor};
use serde::{Deserialize, Deserializer};
use serde_json::{Value, json};
use std::fmt;

struct Restricted(Value);
impl<'de> Deserialize<'de> for Restricted {
    fn deserialize<D: Deserializer<'de>>(d: D) -> std::result::Result<Self, D::Error> {
        struct V;
        impl<'de> Visitor<'de> for V {
            type Value = Restricted;
            fn expecting(&self, f: &mut fmt::Formatter) -> fmt::Result {
                f.write_str("ASCII/u64 JSON")
            }
            fn visit_bool<E: de::Error>(self, v: bool) -> std::result::Result<Restricted, E> {
                Ok(Restricted(json!(v)))
            }
            fn visit_u64<E: de::Error>(self, v: u64) -> std::result::Result<Restricted, E> {
                Ok(Restricted(json!(v)))
            }
            fn visit_unit<E: de::Error>(self) -> std::result::Result<Restricted, E> {
                Ok(Restricted(Value::Null))
            }
            fn visit_str<E: de::Error>(self, v: &str) -> std::result::Result<Restricted, E> {
                if !v.bytes().all(|b| (32..=126).contains(&b)) {
                    return Err(E::custom("non-printable ASCII"));
                }
                Ok(Restricted(json!(v)))
            }
            fn visit_string<E: de::Error>(self, v: String) -> std::result::Result<Restricted, E> {
                self.visit_str(&v)
            }
            fn visit_seq<A: SeqAccess<'de>>(
                self,
                mut a: A,
            ) -> std::result::Result<Restricted, A::Error> {
                let mut out = Vec::new();
                while let Some(Restricted(v)) = a.next_element()? {
                    out.push(v);
                }
                Ok(Restricted(Value::Array(out)))
            }
            fn visit_map<A: MapAccess<'de>>(
                self,
                mut a: A,
            ) -> std::result::Result<Restricted, A::Error> {
                let mut out = serde_json::Map::new();
                while let Some(k) = a.next_key::<String>()? {
                    if !k.bytes().all(|b| (32..=126).contains(&b)) || out.contains_key(&k) {
                        return Err(de::Error::custom("duplicate/non-ASCII key"));
                    }
                    let Restricted(v) = a.next_value()?;
                    out.insert(k, v);
                }
                Ok(Restricted(Value::Object(out)))
            }
        }
        d.deserialize_any(V)
    }
}

pub fn parse(raw: &[u8]) -> Result<Value> {
    let v = serde_json::from_slice::<Restricted>(raw)
        .map_err(|e| Error::reject("CODEC", e.to_string()))?
        .0;
    if encode(&v)? != raw {
        return Err(Error::reject(
            "NONCANONICAL",
            "exact canonical bytes required",
        ));
    }
    Ok(v)
}
pub fn encode(v: &Value) -> Result<Vec<u8>> {
    fn emit(v: &Value, out: &mut Vec<u8>) -> Result<()> {
        match v {
            Value::Null => out.extend_from_slice(b"null"),
            Value::Bool(true) => out.extend_from_slice(b"true"),
            Value::Bool(false) => out.extend_from_slice(b"false"),
            Value::Number(n) => {
                let n = n
                    .as_u64()
                    .ok_or_else(|| Error::reject("CODEC", "u64 required"))?;
                out.extend_from_slice(n.to_string().as_bytes());
            }
            Value::String(s) => {
                if !s.bytes().all(|b| (32..=126).contains(&b)) {
                    return Err(Error::reject("CODEC", "printable ASCII required"));
                }
                out.extend_from_slice(&serde_json::to_vec(s).unwrap());
            }
            Value::Array(a) => {
                out.push(b'[');
                for (i, v) in a.iter().enumerate() {
                    if i > 0 {
                        out.push(b',');
                    }
                    emit(v, out)?;
                }
                out.push(b']');
            }
            Value::Object(m) => {
                let mut keys: Vec<_> = m.keys().collect();
                keys.sort_unstable();
                out.push(b'{');
                for (i, k) in keys.into_iter().enumerate() {
                    if i > 0 {
                        out.push(b',');
                    }
                    emit(&Value::String(k.clone()), out)?;
                    out.push(b':');
                    emit(&m[k], out)?;
                }
                out.push(b'}');
            }
        }
        Ok(())
    }
    let mut out = Vec::new();
    emit(v, &mut out)?;
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn exact_vectors_and_rejections() {
        for s in [
            r#"{}"#,
            r#"{"a":1,"b":2}"#,
            r#"[2,1]"#,
            r#"{"s":"\""}"#,
            r#"{"s":"\\"}"#,
            r#"{"s":"/"}"#,
            r#"{"n":18446744073709551615}"#,
            r#"[false,null,1,"1"]"#,
        ] {
            assert_eq!(encode(&parse(s.as_bytes()).unwrap()).unwrap(), s.as_bytes());
        }
        for s in [
            "-0",
            "1.0",
            "1e0",
            "18446744073709551616",
            "{}\n",
            r#"{"x":1,"x":2}"#,
            r#"{"s":"\u0061"}"#,
            r#"{"s":"\/"}"#,
            r#"{"s":"\n"}"#,
            r#"{"b":2,"a":1}"#,
        ] {
            assert!(parse(s.as_bytes()).is_err(), "{s}");
        }
    }
    #[test]
    fn encoder_rejects_unsupported_values_without_normalizing_them() {
        for v in [
            json!(-1),
            json!(1.0),
            json!("\n"),
            json!("\u{e9}"),
            json!({"\u{e9}":1}),
        ] {
            assert!(encode(&v).is_err());
        }
        assert_eq!(
            encode(&json!({"z":0,"a":[2,1]})).unwrap(),
            br#"{"a":[2,1],"z":0}"#
        );
    }
}
