# gateway/ — CLAUDE.md

Inherits the root `CLAUDE.md` and `docs/ARCHITECTURE.md`; this file only tightens.
Anything marked **(planned)** does not exist yet: build it before documenting it as
real, and remove the marker in the same commit.

## 1. Purpose and boundary

The gateway is the hub and the **only owner of persistent state**. It:

- serves the REST + WebSocket API that `web/`, `strategies/`, and `mcp/` use (§5);
- adapts real market-data providers behind one read-only trait (§7);
- caches bars in SQLite and owns every table in ARCHITECTURE §8 (§8);
- supervises the OCaml engine as a child process over JSON-RPC stdio (§6);
- hosts the game layer (XP, seasons, achievements) as data-driven rules.

Hard limits, in addition to the root non-negotiables:

- **Paper money only (ADR 0003).** Provider adapters expose market data and nothing
  else. No order, account, or auth-to-brokerage method exists on any trait, struct,
  or HTTP client. A brokerage SDK crate in `Cargo.toml` is a rejected change.
- **Never calls the Anthropic API.** No `anthropic` crate, no prompt strings, no
  model names. AI reaches the simulator through `mcp/`, which calls us over HTTP.
- **Binds `127.0.0.1` only** (ARCHITECTURE §11). `main.rs` hard-codes
  `Ipv4Addr::LOCALHOST`; the port comes from `TRADE_GATEWAY_PORT` (default 8787).
- **Secrets from env, never logged.** Provider keys live in `.env`; wrap them in a
  `Secret` newtype whose `Debug` prints `[redacted]` **(planned)**.
- **Deterministic by delegation.** The gateway never computes fills, P&L, or
  metrics itself; it forwards to the engine and persists what comes back.

## 2. Directory layout

```
gateway/
├── Cargo.toml  Cargo.lock  rustfmt.toml  Makefile   # lockfile is committed
├── src/
│   ├── main.rs         binary: env config, tracing to stderr, bind, graceful shutdown
│   ├── lib.rs          `pub fn app() -> Router`; fallbacks for 404/405
│   ├── error.rs        `GatewayError` (thiserror) + IntoResponse → {error:{code,message}}
│   ├── api/            one module per ARCHITECTURE §4 resource, each with `router()`
│   │   ├── mod.rs      mounts everything under `/api/v1`
│   │   ├── health.rs   GET /health
│   │   ├── symbols.rs  bars.rs  quote.rs                                           (planned)
│   │   ├── sessions.rs orders.rs runs.rs board.rs strategies.rs game.rs             (planned)
│   │   └── extract.rs  Json/Path/Query wrappers whose rejections are GatewayError  (planned)
│   ├── ws/             hub.rs (broadcast per topic), topics.rs (parse/validate), conn.rs (planned)
│   ├── providers/      mod.rs (MarketData trait, Provider enum, select_from_env),
│   │                   yahoo.rs alpaca.rs polygon.rs finnhub.rs, cache.rs, ratelimit.rs (planned)
│   ├── engine/         supervisor.rs (child lifecycle), rpc.rs (request/response),
│   │                   types.rs (serde mirror of ARCHITECTURE §3)                     (planned)
│   ├── db/             mod.rs (pool, migrate), sessions.rs orders.rs fills.rs marks.rs
│   │                   bars.rs board.rs strategies.rs journal.rs game.rs events.rs   (planned)
│   ├── game/           xp.rs seasons.rs achievements.rs + achievements.toml           (planned)
│   ├── config.rs       `Config::from_env()`; the only place std::env is read          (planned)
│   └── types.rs        newtypes: Micro, Symbol, Timeframe, SessionId, OrderId, RunId  (planned)
├── migrations/         NNNN_slug.sql, applied in order at startup                       (planned)
└── tests/              contract tests driving `app()` in-process; fixtures/ for providers
    └── health.rs
```

## 3. Toolchain and setup

| Tool | Version | Notes |
|---|---|---|
| rustc / cargo | 1.99 stable | `rust-version = "1.99"` in `Cargo.toml`; edition 2024 |
| rustfmt, clippy | from rustup | `make setup` runs `rustup component add rustfmt clippy` (best-effort, `-` prefixed) |
| CI | `.github/workflows/ci.yml` job `gateway` | `dtolnay/rust-toolchain@stable` with `components: rustfmt, clippy`, `Swatinem/rust-cache@v2` with `workspaces: gateway`, then `make gateway-check && make gateway-test` |

Path filter: the job runs only when `gateway/**` or the root `Makefile` changes.
No system packages are needed today; adding `sqlx`/`reqwest` with rustls keeps it so.

## 4. Commands

Run from the repo root as `make gateway-<target>` or from `gateway/` as `make <target>`.
Every cargo invocation passes `--locked`: if `Cargo.lock` is stale the command fails
instead of silently rewriting it.

| Target | Runs | Use when |
|---|---|---|
| `setup` | `rustup component add rustfmt clippy` | once per machine |
| `build` | `cargo build --locked` | compile lib + bin |
| `check` | `cargo fmt --all -- --check` then `cargo clippy --all-targets --locked -- -D warnings` | before every commit; CI runs it |
| `test` | `cargo test --locked` | unit tests in `src/`, contract tests in `tests/`, doctests |
| `fmt` | `cargo fmt --all` | fix what `check` reported |
| `run` | `cargo run --locked` | serve on `127.0.0.1:${TRADE_GATEWAY_PORT:-8787}`; `RUST_LOG=debug` for more |
| `clean` | `cargo clean` | nuke `target/` (gitignored) |

Smoke test after `make run` in another pane:
```bash
curl -s http://127.0.0.1:8787/api/v1/health   # {"status":"ok","engine":"down","provider":"yahoo"}
```

## 5. API contract

Source of truth: ARCHITECTURE §4. Base path `/api/v1` (`api::PREFIX`). JSON in, JSON
out, `content-type: application/json`. No auth in Phases 0–2.

### 5.1 Routes

| Method & path | Handler (module::fn) | Request struct | Response struct |
|---|---|---|---|
| `GET /health` | `api::health::get_health` | — | `HealthResponse {status, engine: "up"\|"down", provider}` |
| `GET /symbols?q=` | `api::symbols::search` (planned) | `SearchQuery {q}` | `Vec<SymbolInfo {symbol, name, exchange}>` |
| `GET /bars/{symbol}?tf=&from=&to=` | `api::bars::list` (planned) | `BarsQuery {tf: Timeframe, from, to}` | `Vec<Bar {t, o, h, l, c, v}>` prices as `_micro` i64 |
| `GET /quote/{symbol}` | `api::quote::get` (planned) | — | `Quote {symbol, t, bid_micro, ask_micro, last_micro}` |
| `POST /sessions` | `api::sessions::create` (planned) | `CreateSession {name, start_cash_micro, mode, start_time, seed}` | `Session` (201) |
| `GET /sessions`, `GET /sessions/{id}` | `api::sessions::{list,get}` (planned) | — | `Vec<Session>` / `Session` |
| `POST /sessions/{id}/orders` | `api::orders::submit` (planned) | `SubmitOrder` = engine `order.submit` params minus `session_id` | `OrderAck {order_id, status, reason?}` (202) |
| `DELETE /sessions/{id}/orders/{order_id}` | `api::orders::cancel` (planned) | — | `{status}` |
| `GET /sessions/{id}/portfolio` | `api::sessions::portfolio` (planned) | — | engine `Portfolio` |
| `GET /sessions/{id}/fills?since=` | `api::sessions::fills` (planned) | `FillsQuery {since}` | `Vec<Fill>` |
| `POST /sessions/{id}/runs` | `api::runs::start` (planned) | `StartRun {strategy_id, version, symbols, tf}` | `Run` (202) |
| `GET /runs/{id}` | `api::runs::get` (planned) | — | `Run {.., status, metrics?}` |
| `GET /board`, `POST /board/cards`, `PATCH /board/cards/{id}` | `api::board::{get,create_card,patch_card}` (planned) | `CreateCard`, `PatchCard {column?, position?, notes?}` | `Board {columns: [..cards]}` / `Card` |
| `GET /strategies`, `POST /strategies`, `GET /strategies/{id}/versions` | `api::strategies::{list,create,versions}` (planned) | `CreateStrategy {name, owner, source}` | `Strategy` / `Vec<StrategyVersion>` |
| `GET /game/profile`, `/game/leaderboard`, `/game/season` | `api::game::{profile,leaderboard,season}` (planned) | `?actor=` | `Profile`, `Vec<LeaderboardRow>`, `Season` |

Session `mode` is validated against `{"backtest","paper"}` at the serde layer (an
enum, not a string); anything else is `bad_request` (ADR 0003).

### 5.2 Errors

Every failure, including unknown routes and wrong methods, is
`{"error": {"code": "<snake_case>", "message": "<text>"}}`. Codes are part of the
contract; renaming one is a breaking change. From `error.rs`:

| `GatewayError` | HTTP | `code` | When |
|---|---|---|---|
| `BadRequest(msg)` | 400 | `bad_request` | validation, bad query/body, unknown `mode`/`tf` |
| `NotFound(msg)` | 404 | `not_found` | unknown route, session, order, run, card |
| `MethodNotAllowed` | 405 | `method_not_allowed` | route exists, method does not |
| `EngineDown(msg)` | 503 | `engine_down` | engine child absent, restarting, or timed out |
| `Provider(msg)` | 502 | `provider` | upstream HTTP/parse failure, rate limit exhausted |
| `Config(msg)` | 500 | `config` | bad env at startup (never reaches a client in practice) |
| `Io(err)` | 500 | `io` | socket/file/subprocess I/O |
| `Internal(msg)` | 500 | `internal` | everything else; also logged at `error` |

Handlers return `Result<Json<T>, GatewayError>` and use `?`. Messages are client
visible: never interpolate a key, a token, or a full upstream URL with query string.

### 5.3 WebSocket (planned)

`GET /ws` upgrades. Client → server:
`{"type":"subscribe","topics":[...]}` and `{"type":"unsubscribe","topics":[...]}`.
Server → client: `{"type", "topic", "t", "payload"}` where `type` ∈
`subscribed | unsubscribed | bar | quote | fill | mark | order | card | run | lagged | error`.

Topic grammar (`ws::topics::Topic`, parsed and validated, never string-matched ad hoc):
`quotes:{SYMBOL}` · `bars:{SYMBOL}:{1m|5m|1d}` · `session:{id}` (fills, marks, order
updates) · `board` · `runs:{id}`. Unknown topic → one `error` message with
`code: "bad_request"`, connection stays open.

Backpressure: the hub holds one bounded `tokio::sync::broadcast` channel per live
topic (capacity 1024). Each connection has a bounded outbound queue (256). A
receiver that falls behind gets `RecvError::Lagged(n)`; the hub sends
`{"type":"lagged","topic","payload":{"dropped":n}}` and the client must resubscribe
and backfill via REST (`/bars`, `/sessions/{id}/fills`). A connection whose outbound
queue is full for more than 5 s is closed with code 1013 and reason `slow consumer`.
Messages within a topic are in order; across topics no ordering is promised.

## 6. Engine supervision (planned)

`engine::supervisor` owns exactly one child built with `tokio::process::Command`
from `TRADE_ENGINE_BIN` (add it to `.env.example` in the same change and say so in
the report). Lifecycle:

1. Spawn with piped stdin/stdout/stderr, `kill_on_drop(true)`.
2. **Framing**: one JSON-RPC 2.0 object per line, UTF-8, `\n` terminated. Writer is a
   single task fed by an `mpsc` so lines never interleave; it calls `flush()` after
   every line (the engine blocks on `read_line`). Reader uses `BufReader::lines()`.
   stderr is forwarded line by line to `tracing` at target `engine`, never parsed.
3. **Correlation**: `id` is a monotonically increasing `u64`; pending requests live in
   `HashMap<u64, oneshot::Sender<Result<Value, RpcError>>>`. A line without `id` is a
   notification (`fill`, `reject`, `mark`) and goes to the events channel → persisted
   to `fills`/`marks`/`events` and fanned out on `session:{id}`.
4. **Timeouts**: 5 s per request; 120 s for `backtest.run` and `replay.load`.
   A timeout is `EngineDown` to the caller and triggers step 5.
5. **Restart**: on exit, EOF, or timeout → `/health` reports `engine: "down"`, orders
   return 503 `engine_down`, the child is killed and respawned with backoff
   250 ms doubling to 10 s, giving up after 5 consecutive failures (health stays
   `down`; an operator restarts the gateway).
6. **State replay**: after a respawn, for each session with `closed_at IS NULL`, send
   `session.create` with the persisted parameters, then replay that session's
   `events` rows in `seq` order (`market.bar`, `order.submit`, `order.cancel`). The
   engine is deterministic given inputs and seed, so the rebuilt portfolio must equal
   the last persisted `marks` row; a mismatch is logged at `error` and the session is
   marked `closed_at = now` with reason `replay_mismatch`.

The gateway never sends a request the engine protocol does not list; the serde
types in `engine::types` mirror ARCHITECTURE §3 field for field, in micro-units.

## 7. Providers (planned)

```rust
pub trait MarketData: Send + Sync {
    fn name(&self) -> &'static str;
    fn search(&self, q: &str) -> impl Future<Output = Result<Vec<SymbolInfo>, ProviderError>> + Send;
    fn bars(&self, symbol: &Symbol, tf: Timeframe, from: Utc, to: Utc)
        -> impl Future<Output = Result<Vec<Bar>, ProviderError>> + Send;
    fn quote(&self, symbol: &Symbol) -> impl Future<Output = Result<Quote, ProviderError>> + Send;
    fn subscribe_quotes(&self, symbols: &[Symbol]) -> mpsc::Receiver<Quote>;
}
```

- **No order methods, ever.** Not `submit`, not `account`, not `positions`. A trait
  method that writes anything to a provider is a rejected change (ADR 0003).
- `Provider` is an enum over the concrete adapters (enum dispatch; no `dyn`, no
  `async_trait`). `providers::select_from_env()` reads `TRADE_DATA_PROVIDER`
  (`yahoo` default, `alpaca`, `polygon`, `finnhub`) and the matching keys:

| Provider | Env | Streaming |
|---|---|---|
| `yahoo` | none | no: `subscribe_quotes` polls `quote` every 5 s |
| `alpaca` | `ALPACA_KEY_ID`, `ALPACA_SECRET_KEY` | WS |
| `polygon` | `POLYGON_API_KEY` | WS |
| `finnhub` | `FINNHUB_API_KEY` | WS |

- **Rate limiting**: a token bucket per provider in `providers::ratelimit` sized to the
  provider's free tier; exhaustion waits up to 2 s then returns `Provider("rate
  limited")`. **Caching**: bars go through `providers::cache` → the `bars` table; a
  request only fetches the gaps in `[from, to]`. Quotes have a 1 s in-memory TTL.
- **Testing**: every adapter has a pure `parse_bars(&[u8])`/`parse_quote(&[u8])` layer
  tested against recorded responses in `tests/fixtures/<provider>/*.json` (secrets
  scrubbed before committing). Live calls are `#[ignore]` and run only with
  `TRADE_LIVE_PROVIDER_TESTS=1`. HTTP via `reqwest` with `rustls-tls`, 10 s timeout.

## 8. Persistence (planned)

- Engine: `sqlx` (`sqlite`, `runtime-tokio`, `migrate`), runtime `sqlx::query()` only,
  no `query!` macros, so CI needs no database. Path: `${TRADE_DATA_DIR:-./data}/trade.db`,
  created on first run. Pragmas at open: `journal_mode=WAL`, `synchronous=NORMAL`,
  `foreign_keys=ON`, `busy_timeout=5000`.
- Migrations: `migrations/NNNN_slug.sql`, embedded with `sqlx::migrate!()`, applied
  at startup before the listener binds. `0001_init.sql` is ARCHITECTURE §8 verbatim.
  Never edit an applied migration; add the next number.
- **Money and quantity are `INTEGER` micro-units** (`*_micro`, i64), mapped to the
  `Micro` newtype. Times are `TEXT` RFC 3339 UTC. Floats appear only in
  `metrics_json` (ratios the engine computed).
- Indexes: `bars(symbol, tf, t)` UNIQUE, `fills(session_id, t)`, `orders(session_id,
  status)`, `marks(session_id, t)`, `events(session_id, seq)` UNIQUE, `cards(column,
  position)`, `journal(run_id)`, `season_scores(season_id, score DESC)`.
- `events(session_id, seq, t, kind, payload_json)` mirrors every request the gateway
  sent the engine and every notification it received, in order. It is the replay
  source for §6 step 6 and for byte-for-byte reproduction.
- Backup is copying the file: stop the gateway, copy `trade.db` plus `trade.db-wal`
  and `trade.db-shm`, or run `sqlite3 data/trade.db ".backup out.db"` while live.
- One `db::<table>` module per table with typed functions; no SQL strings outside `db/`.

## 9. Code conventions

- `cargo fmt` clean; `cargo clippy --all-targets -- -D warnings` clean. `Cargo.toml`
  lints: `unsafe_code = "forbid"`, `missing_docs = "warn"` (so every `pub` item is
  documented), `clippy::unwrap_used` and `clippy::expect_used` = `deny`.
- Errors: `thiserror` enums, `?` everywhere, convert at module edges with `From`.
  No `unwrap`/`expect` outside `#[cfg(test)]` and `tests/` (those opt in with
  `#![allow(clippy::expect_used)]`). No `panic!` on a request path.
- `tracing`: one span per request (`tower_http::trace::TraceLayer` with a request id,
  planned), `info` for lifecycle, `debug` for per-message, `error` only for 5xx and
  engine faults. Logs go to stderr. Never log a header, a key, or a request body.
- Newtypes at the domain layer: `Micro(i64)`, `Symbol` (uppercase, validated),
  `Timeframe` enum, `SessionId`, `OrderId`, `RunId`. Raw `i64`/`String` for these in a
  function signature is a review finding.
- `serde` derives only on boundary structs (`api/*`, `engine/types.rs`,
  `providers/*/wire`, `db` rows). Domain types convert via `From`/`TryFrom`.
- Blocking work (`std::fs`, CPU-heavy parsing of big fixtures) goes through
  `tokio::task::spawn_blocking`; sqlx is already async.
- Module docs (`//!`) state what the module owns and which ARCHITECTURE section it
  implements. Tests live next to the code for units, in `tests/` for contracts.

## 10. Recipes

**Add a REST route**
1. Add the row to ARCHITECTURE §4 if it is new (same commit).
2. Create `src/api/<resource>.rs` with request/response structs (serde) and `pub fn router() -> Router`.
3. `pub mod <resource>;` in `src/api/mod.rs` and `.merge(<resource>::router())`.
4. Handler signature: extractors first, body last; return `Result<Json<T>, GatewayError>`.
5. Contract test in `tests/<resource>.rs` via `app().oneshot(...)`: status, `content-type`, body, and one error case.

**Add a WS topic**
1. Add the variant to `ws::topics::Topic` and its `FromStr`/`Display`; update §5.3 and ARCHITECTURE §4.
2. Register the producer: whoever has the data calls `hub.publish(topic, Message)`.
3. Unit-test parse/format; contract-test subscribe → message → `lagged` on overflow.

**Add a provider**
1. `src/providers/<name>.rs`: client struct, `wire` structs, pure `parse_*` fns, `impl MarketData`.
2. Add the variant to the `Provider` enum and `select_from_env()`; read its env vars through `config.rs`.
3. Document the env vars in `.env.example` (root file: say so in the report) and the table in §7.
4. Record fixtures into `tests/fixtures/<name>/`, scrub keys, write parse tests; `#[ignore]` live test.

**Add a migration**
1. `migrations/NNNN_slug.sql` (next number, forward only); update ARCHITECTURE §8 in the same commit.
2. Add or change the `db::<table>` functions and their row structs.
3. Test: open a temp DB, run `sqlx::migrate!()`, exercise the new functions.

**Add an achievement**
1. Add a `[[achievement]]` entry to `src/game/achievements.toml` (`id`, `title`, `rule`, `xp`).
2. If the `rule` kind is new, add it to `game::achievements::Rule` and its evaluator.
3. Test the evaluator with a fixture profile; achievements are data, not code paths.

## 11. Pitfalls

- **axum extractor order**: the body-consuming extractor (`Json`, `String`, `Bytes`)
  must be the last argument; `State`, `Path`, `Query`, headers come first.
- **Built-in rejections are not enveloped**: a bad `Json` body returns axum's plain
  text 400/422 until `api::extract` wraps it. Use the wrappers once they exist.
- **Blocking on the runtime**: never `std::thread::sleep`, `std::fs`, or a sync HTTP
  client inside an `async fn`; use tokio equivalents or `spawn_blocking`.
- **Broadcast lag is normal**: `RecvError::Lagged` is not a bug; handle it with the
  `lagged` message, never by growing the channel unbounded.
- **`Cargo.lock` is committed** and every target runs `--locked`; after changing
  `Cargo.toml` run `cargo update -p <crate>` (or a plain build) and commit the lock.
- **`-D warnings` covers dev-dependencies and tests** (`--all-targets`); an unused
  import in `tests/` fails `make check`.
- **`127.0.0.1` vs `0.0.0.0`**: the bind address is hard-coded; do not make it
  configurable "for Docker" without an ADR and auth.
- **Nested routers and fallbacks**: set `fallback`/`method_not_allowed_fallback` once
  on the outer router in `lib.rs` (already done) and nowhere else; the contract
  tests for 404/405 catch a regression.
- **`TRADE_GATEWAY_PORT` is parsed, not trusted**: a non-port value exits 1 with
  `configuration error`; tests use `oneshot` with no socket, never a fixed port.

## 12. Definition of done (gateway change)

- [ ] `make gateway-check` and `make gateway-test` pass locally from a clean tree.
- [ ] New route/topic/table/env var is in ARCHITECTURE §4/§8 and here, same commit.
- [ ] Every `pub` item documented; no `unwrap`/`expect` outside tests; no `unsafe`.
- [ ] Contract test for every new route and error path; fixture test for every parser.
- [ ] No provider write methods, no brokerage crates, no `live_trading`-style flag.
- [ ] No key, token, or `data/` content in the diff; `Cargo.lock` updated if deps changed.
- [ ] Commits atomic and Conventional (`feat|fix|docs|test|refactor|build(gateway): …`),
      attributed, rebased on `origin/main`; report lists SHAs and commands actually run.

## 13. Phase plan

| Phase | Deliverables (all planned unless listed in §2 without a marker) |
|---|---|
| **1** | `config.rs`; `providers/yahoo.rs` history + `cache.rs` into `bars`; `db/` with `0001_init.sql`; `engine/` supervisor + rpc with replay; `api/` `symbols`, `bars`, `quote`, `sessions`, `orders`; `ws/` hub with `bars:*`, `quotes:*`, `session:*`; health reports real engine/provider state |
| **2** | `api/runs` launching the strategy runner, `api/board`, `api/strategies`, `journal` table and `events` mirror complete; WS `board`, `runs:*`; `api/extract` wrappers; request-id tracing |
| **3** | `game/` (XP, seasons, leaderboard, `achievements.toml`); `alpaca`, `polygon`, `finnhub` adapters with fixtures; rate limiting; backup/restore notes verified |
