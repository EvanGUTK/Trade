//! REST routes under `/api/v1` (ARCHITECTURE §4).
//!
//! One submodule per resource in the §4 table. Each exposes `router()` returning
//! its routes relative to `/api/v1`; [`router`] here mounts them all.

pub mod health;

use axum::Router;

/// Path prefix every REST route lives under.
pub const PREFIX: &str = "/api/v1";

/// All REST routes, already prefixed with [`PREFIX`].
pub fn router() -> Router {
    Router::new().nest(PREFIX, Router::new().merge(health::router()))
}
