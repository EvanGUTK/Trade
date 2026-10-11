//! Binary entry point. Reads config from the environment, logs to stderr,
//! binds `127.0.0.1:<TRADE_GATEWAY_PORT or 8787>`, serves [`trade_gateway::app`],
//! and shuts down gracefully on ctrl-c or SIGTERM.

use std::net::{Ipv4Addr, SocketAddr};

use tokio::net::TcpListener;
use tokio::signal;
use tracing_subscriber::EnvFilter;

use trade_gateway::{GatewayError, app};

/// Port from ARCHITECTURE §9 when `TRADE_GATEWAY_PORT` is unset.
const DEFAULT_PORT: u16 = 8787;

#[tokio::main]
async fn main() {
    init_tracing();
    if let Err(err) = run().await {
        tracing::error!(error = %err, "gateway exited with error");
        std::process::exit(1);
    }
}

async fn run() -> Result<(), GatewayError> {
    let port = port_from_env()?;
    // Localhost only (ARCHITECTURE §11). Never 0.0.0.0.
    let addr = SocketAddr::from((Ipv4Addr::LOCALHOST, port));
    let listener = TcpListener::bind(addr).await?;
    tracing::info!(%addr, "gateway listening");
    axum::serve(listener, app())
        .with_graceful_shutdown(shutdown_signal())
        .await?;
    tracing::info!("gateway stopped");
    Ok(())
}

/// Logs go to stderr so stdout stays free; `RUST_LOG` overrides the `info` default.
fn init_tracing() {
    let filter = EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info"));
    tracing_subscriber::fmt()
        .with_env_filter(filter)
        .with_writer(std::io::stderr)
        .init();
}

fn port_from_env() -> Result<u16, GatewayError> {
    match std::env::var("TRADE_GATEWAY_PORT") {
        Ok(raw) => raw.trim().parse().map_err(|_| {
            GatewayError::Config(format!(
                "TRADE_GATEWAY_PORT must be a TCP port number, got {raw:?}"
            ))
        }),
        Err(std::env::VarError::NotPresent) => Ok(DEFAULT_PORT),
        Err(err) => Err(GatewayError::Config(format!("TRADE_GATEWAY_PORT: {err}"))),
    }
}

/// Resolves on ctrl-c or SIGTERM. If a handler cannot be installed we log and
/// keep serving rather than shut down immediately.
async fn shutdown_signal() {
    let ctrl_c = async {
        if let Err(err) = signal::ctrl_c().await {
            tracing::warn!(error = %err, "cannot install ctrl-c handler");
            std::future::pending::<()>().await;
        }
    };

    #[cfg(unix)]
    let terminate = async {
        match signal::unix::signal(signal::unix::SignalKind::terminate()) {
            Ok(mut sigterm) => {
                sigterm.recv().await;
            }
            Err(err) => {
                tracing::warn!(error = %err, "cannot install SIGTERM handler");
                std::future::pending::<()>().await;
            }
        }
    };
    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();

    tokio::select! {
        () = ctrl_c => {},
        () = terminate => {},
    }
    tracing::info!("shutdown signal received, draining connections");
}
