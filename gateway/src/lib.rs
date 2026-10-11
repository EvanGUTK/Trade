//! `trade-gateway`: the hub of Trade.
//!
//! Owns market-data provider adapters, the bar cache, the REST + WebSocket API,
//! SQLite persistence, and the engine subprocess. Paper money only (ADR 0003):
//! nothing in this crate can reach a brokerage. The library exposes [`app`]; the
//! binary in `main.rs` only binds `127.0.0.1` and serves it, so tests drive the
//! router in-process with `tower::ServiceExt::oneshot`.

pub mod api;
pub mod error;

use axum::Router;
use axum::http::{Method, Uri};

pub use error::GatewayError;

/// The complete gateway router: REST under `/api/v1`, JSON error envelope for
/// unknown routes and methods.
pub fn app() -> Router {
    Router::new()
        .merge(api::router())
        .fallback(not_found)
        .method_not_allowed_fallback(method_not_allowed)
}

async fn not_found(method: Method, uri: Uri) -> GatewayError {
    GatewayError::NotFound(format!("no route for {method} {uri}"))
}

async fn method_not_allowed() -> GatewayError {
    GatewayError::MethodNotAllowed
}
