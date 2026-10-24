use serde::{Deserialize, Deserializer, Serialize, Serializer};
use sha2::{Digest, Sha256};

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ContentDigest([u8; 32]);
impl ContentDigest {
    pub fn of(bytes: &[u8]) -> Self {
        Self(Sha256::digest(bytes).into())
    }
    pub fn from_hasher(h: Sha256) -> Self {
        Self(h.finalize().into())
    }
    pub fn hex(&self) -> String {
        self.0.iter().map(|b| format!("{b:02x}")).collect()
    }
}
impl Serialize for ContentDigest {
    fn serialize<S: Serializer>(&self, s: S) -> std::result::Result<S::Ok, S::Error> {
        s.serialize_str(&self.hex())
    }
}
impl<'de> Deserialize<'de> for ContentDigest {
    fn deserialize<D: Deserializer<'de>>(d: D) -> std::result::Result<Self, D::Error> {
        let s = String::deserialize(d)?;
        if s.len() != 64
            || !s
                .bytes()
                .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
        {
            return Err(serde::de::Error::custom("lowercase SHA-256 required"));
        }
        let mut out = [0; 32];
        for (i, b) in out.iter_mut().enumerate() {
            *b = u8::from_str_radix(&s[2 * i..2 * i + 2], 16).unwrap();
        }
        Ok(Self(out))
    }
}

/// Different identity roles cannot be substituted even for equal digest bytes.
/// ```compile_fail
/// use a0_mechanical_core::identity::{ContentDigest, SourceIdentity, ExecutionIdentity};
/// let execution = ExecutionIdentity::declared(ContentDigest::of(b"same"));
/// let source: SourceIdentity = execution;
/// ```
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SourceIdentity(ContentDigest);
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ExecutionIdentity(ContentDigest);
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CheckpointIdentity(ContentDigest);
/// Cache identity is not a checkpoint or a source, even for identical bytes.
/// ```compile_fail
/// use a0_mechanical_core::identity::{CacheIdentity, ContentDigest, SourceIdentity};
/// let cache = CacheIdentity::declared(ContentDigest::of(b"same"));
/// let source: SourceIdentity = cache;
/// ```
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CacheIdentity(ContentDigest);
macro_rules! role {
    ($name:ident) => {
        impl $name {
            pub fn declared(digest: ContentDigest) -> Self {
                Self(digest)
            }
        }
        impl Serialize for $name {
            fn serialize<S: Serializer>(&self, s: S) -> std::result::Result<S::Ok, S::Error> {
                #[derive(Serialize)]
                struct Wire<'a> {
                    role: &'static str,
                    sha256: &'a ContentDigest,
                }
                Wire {
                    role: stringify!($name),
                    sha256: &self.0,
                }
                .serialize(s)
            }
        }
        impl<'de> Deserialize<'de> for $name {
            fn deserialize<D: Deserializer<'de>>(d: D) -> std::result::Result<Self, D::Error> {
                #[derive(Deserialize)]
                #[serde(deny_unknown_fields)]
                struct Wire {
                    role: String,
                    sha256: ContentDigest,
                }
                let v = Wire::deserialize(d)?;
                if v.role != stringify!($name) {
                    return Err(serde::de::Error::custom("identity role mismatch"));
                }
                Ok(Self(v.sha256))
            }
        }
    };
}
role!(SourceIdentity);
role!(ExecutionIdentity);
role!(CheckpointIdentity);
role!(CacheIdentity);

/// Byte count is always an unsigned 64-bit length, never an identity role.
pub type ByteLength = u64;
