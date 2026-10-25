//! Internal experimental byte mechanisms; not a public runtime API.
pub mod codec;
pub mod identity;
pub mod inventory;
pub use inventory::{Error, Result, validate_name};
