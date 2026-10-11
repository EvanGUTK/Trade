//! Contract tests for `GET /api/v1/health` and the error envelope, driven
//! in-process through `tower::ServiceExt::oneshot` (no socket, no port).

#![allow(clippy::expect_used)]

use axum::body::Body;
use axum::http::{Request, StatusCode, header};
use http_body_util::BodyExt;
use tower::ServiceExt;

use trade_gateway::app;

async fn send(method: &str, uri: &str) -> (StatusCode, Option<String>, serde_json::Value) {
    let request = Request::builder()
        .method(method)
        .uri(uri)
        .body(Body::empty())
        .expect("well-formed request");
    let response = app().oneshot(request).await.expect("router is infallible");
    let status = response.status();
    let content_type = response
        .headers()
        .get(header::CONTENT_TYPE)
        .and_then(|v| v.to_str().ok())
        .map(str::to_owned);
    let bytes = response
        .into_body()
        .collect()
        .await
        .expect("body readable")
        .to_bytes();
    let json = serde_json::from_slice(&bytes).expect("body is JSON");
    (status, content_type, json)
}

#[tokio::test]
async fn health_reports_ok_engine_down_default_provider() {
    let (status, content_type, json) = send("GET", "/api/v1/health").await;
    assert_eq!(status, StatusCode::OK);
    assert_eq!(content_type.as_deref(), Some("application/json"));
    assert_eq!(
        json,
        serde_json::json!({"status": "ok", "engine": "down", "provider": "yahoo"})
    );
}

#[tokio::test]
async fn unknown_route_uses_error_envelope() {
    let (status, content_type, json) = send("GET", "/api/v1/nope").await;
    assert_eq!(status, StatusCode::NOT_FOUND);
    assert_eq!(content_type.as_deref(), Some("application/json"));
    assert_eq!(json["error"]["code"], "not_found");
    assert!(
        json["error"]["message"]
            .as_str()
            .is_some_and(|m| m.contains("/api/v1/nope")),
        "message names the missing route: {json}"
    );
}

#[tokio::test]
async fn wrong_method_uses_error_envelope() {
    let (status, _, json) = send("POST", "/api/v1/health").await;
    assert_eq!(status, StatusCode::METHOD_NOT_ALLOWED);
    assert_eq!(
        json,
        serde_json::json!({"error": {"code": "method_not_allowed", "message": "method not allowed"}})
    );
}
