//! `GET /api/v1/health` — liveness plus engine and provider status.

use axum::routing::get;
use axum::{Json, Router};
use serde::Serialize;

/// Provider reported until `TRADE_DATA_PROVIDER` selection is wired (Phase 1).
const DEFAULT_PROVIDER: &str = "yahoo";

/// Whether the engine subprocess is answering JSON-RPC.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum EngineStatus {
    /// The engine child is running and the last request succeeded.
    Up,
    /// No engine child yet, or it is restarting.
    Down,
}

/// Response body of `GET /api/v1/health`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct HealthResponse {
    /// Always `"ok"`: if the gateway can answer at all, it is up.
    pub status: &'static str,
    /// Engine subprocess state.
    pub engine: EngineStatus,
    /// Name of the active market-data provider.
    pub provider: String,
}

/// Routes for this resource, relative to `/api/v1`.
pub fn router() -> Router {
    Router::new().route("/health", get(get_health))
}

async fn get_health() -> Json<HealthResponse> {
    Json(HealthResponse {
        status: "ok",
        engine: EngineStatus::Down,
        provider: DEFAULT_PROVIDER.to_owned(),
    })
}
