//! The one error type that crosses the HTTP boundary.
//!
//! Every failed response is `{"error": {"code", "message"}}` with the HTTP status
//! from [`GatewayError::status`] (ARCHITECTURE §4). Handlers return
//! `Result<T, GatewayError>` and use `?`; the `IntoResponse` impl does the rest.
//! Messages are shown to clients, so they must never contain provider keys or
//! other secrets.

use axum::Json;
use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use serde::Serialize;

/// Every error the gateway can return to a client or fail to start with.
#[derive(Debug, thiserror::Error)]
pub enum GatewayError {
    /// The request was malformed or failed validation (400).
    #[error("{0}")]
    BadRequest(String),
    /// The route or resource does not exist (404).
    #[error("{0}")]
    NotFound(String),
    /// The route exists but not for this HTTP method (405).
    #[error("method not allowed")]
    MethodNotAllowed,
    /// The engine subprocess is down or restarting (503).
    #[error("engine unavailable: {0}")]
    EngineDown(String),
    /// A market-data provider failed or rate-limited us (502).
    #[error("provider error: {0}")]
    Provider(String),
    /// Startup configuration from the environment is invalid (500).
    #[error("configuration error: {0}")]
    Config(String),
    /// Socket, file, or subprocess I/O failed (500).
    #[error("i/o error: {0}")]
    Io(#[from] std::io::Error),
    /// Anything else; the message is logged, the client sees it verbatim (500).
    #[error("internal error: {0}")]
    Internal(String),
}

impl GatewayError {
    /// Stable machine-readable code. Part of the API contract: clients may
    /// match on it, so renaming a code is a breaking change.
    #[must_use]
    pub fn code(&self) -> &'static str {
        match self {
            Self::BadRequest(_) => "bad_request",
            Self::NotFound(_) => "not_found",
            Self::MethodNotAllowed => "method_not_allowed",
            Self::EngineDown(_) => "engine_down",
            Self::Provider(_) => "provider",
            Self::Config(_) => "config",
            Self::Io(_) => "io",
            Self::Internal(_) => "internal",
        }
    }

    /// HTTP status this error maps to.
    #[must_use]
    pub fn status(&self) -> StatusCode {
        match self {
            Self::BadRequest(_) => StatusCode::BAD_REQUEST,
            Self::NotFound(_) => StatusCode::NOT_FOUND,
            Self::MethodNotAllowed => StatusCode::METHOD_NOT_ALLOWED,
            Self::EngineDown(_) => StatusCode::SERVICE_UNAVAILABLE,
            Self::Provider(_) => StatusCode::BAD_GATEWAY,
            Self::Config(_) | Self::Io(_) | Self::Internal(_) => StatusCode::INTERNAL_SERVER_ERROR,
        }
    }
}

/// Wire shape of an error response: `{"error": {"code": "...", "message": "..."}}`.
#[derive(Debug, Serialize)]
pub struct ErrorBody {
    /// The single error object.
    pub error: ErrorDetail,
}

/// The `error` object inside [`ErrorBody`].
#[derive(Debug, Serialize)]
pub struct ErrorDetail {
    /// Value of [`GatewayError::code`].
    pub code: &'static str,
    /// Human-readable description, from `Display`.
    pub message: String,
}

impl From<&GatewayError> for ErrorBody {
    fn from(err: &GatewayError) -> Self {
        Self {
            error: ErrorDetail {
                code: err.code(),
                message: err.to_string(),
            },
        }
    }
}

impl IntoResponse for GatewayError {
    fn into_response(self) -> Response {
        let status = self.status();
        if status.is_server_error() {
            tracing::error!(code = self.code(), error = %self, "request failed");
        } else {
            tracing::debug!(code = self.code(), error = %self, "request rejected");
        }
        (status, Json(ErrorBody::from(&self))).into_response()
    }
}

#[cfg(test)]
#[allow(clippy::expect_used)]
mod tests {
    use super::*;

    #[test]
    fn every_variant_has_a_status_and_code() {
        let cases: Vec<(GatewayError, StatusCode, &str)> = vec![
            (
                GatewayError::BadRequest("x".into()),
                StatusCode::BAD_REQUEST,
                "bad_request",
            ),
            (
                GatewayError::NotFound("x".into()),
                StatusCode::NOT_FOUND,
                "not_found",
            ),
            (
                GatewayError::MethodNotAllowed,
                StatusCode::METHOD_NOT_ALLOWED,
                "method_not_allowed",
            ),
            (
                GatewayError::EngineDown("x".into()),
                StatusCode::SERVICE_UNAVAILABLE,
                "engine_down",
            ),
            (
                GatewayError::Provider("x".into()),
                StatusCode::BAD_GATEWAY,
                "provider",
            ),
            (
                GatewayError::Config("x".into()),
                StatusCode::INTERNAL_SERVER_ERROR,
                "config",
            ),
            (
                GatewayError::Io(std::io::Error::other("x")),
                StatusCode::INTERNAL_SERVER_ERROR,
                "io",
            ),
            (
                GatewayError::Internal("x".into()),
                StatusCode::INTERNAL_SERVER_ERROR,
                "internal",
            ),
        ];
        for (err, status, code) in cases {
            assert_eq!(err.status(), status, "{err}");
            assert_eq!(err.code(), code, "{err}");
        }
    }

    #[test]
    fn body_matches_the_documented_envelope() {
        let err = GatewayError::NotFound("session 42".into());
        let json = serde_json::to_value(ErrorBody::from(&err)).expect("serializable");
        assert_eq!(
            json,
            serde_json::json!({"error": {"code": "not_found", "message": "session 42"}})
        );
    }
}
