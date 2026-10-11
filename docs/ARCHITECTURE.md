# Trade — Architecture

Status: Phase 0 contract. Everything here is binding on component CLAUDE.md files
and on code. Change this document in the same commit as the protocol it describes.

## 1. Goals and constraints

- A single developer machine runs the whole stack with `make dev`.
- Paper money only; real market data; deterministic, replayable simulations.
- The UI looks and feels like WeBull: dark, dense, chart-centric, with a kanban
  "Strategy Board" as the game surface.
- A separate Claude agent (the Trader) participates as a player through MCP, with
  persistent memory and a structured journal, and gets measurably better over time.
- Each component is independently buildable, testable, and owned by one worker.

## 2. Components and boundaries

| Component | Process | Talks to | Never talks to |
|---|---|---|---|
| `engine/` (OCaml) | child of gateway, stdio | gateway only | network, disk (except a replay log path handed to it) |
| `gateway/` (Rust) | long-running, port 8787 | providers (HTTPS), engine (stdio), SQLite, clients (REST/WS) | Anthropic API |
| `strategies/` runner (Python) | long-running or per-run | gateway (WS + REST) | engine directly, Anthropic API |
| `mcp/` (Python) | stdio or port 8788 | gateway (REST/WS) | engine directly, Anthropic API |
| `trader/` (Python) | long-running or per-review | mcp (MCP client), Anthropic API | gateway/engine directly |
| `web/` (TS) | Vite dev 5173, static in prod | gateway (REST/WS) | anything else |

The gateway is the hub and the only owner of persistent state. If the Rust gateway
is deferred, a Python FastAPI gateway with the same API is the fallback (ADR 0001).

## 3. Engine protocol (gateway ↔ engine)

JSON-RPC 2.0, newline-delimited, one object per line, over the engine's stdin/stdout.
stderr is for logs only. All money is integer micro-dollars (`int64`, 1 USD =
1_000_000) and all quantities are integer micro-shares to keep the engine exact.
Times are RFC 3339 UTC strings. The engine is single-threaded and processes
requests in order.

Requests (gateway → engine):

| Method | Params | Result |
|---|---|---|
| `session.create` | `{session_id, start_cash, start_time, seed, slippage: {model: "none"\|"bps"\|"spread", bps?}, commission: {per_share_micro, min_micro}}` | `{session_id}` |
| `session.close` | `{session_id}` | `{}` |
| `market.bar` | `{session_id, symbol, bar: {t, o, h, l, c, v}}` — advances the clock to `t` and marks | `{fills: [...], mark: Mark}` |
| `order.submit` | `{session_id, order: {client_id, symbol, side: "buy"\|"sell", qty_micro, type: "market"\|"limit"\|"stop", limit_micro?, stop_micro?, tif: "day"\|"gtc"}}` | `{order_id, status: "accepted"\|"rejected", reason?}` |
| `order.cancel` | `{session_id, order_id}` | `{status}` |
| `portfolio.get` | `{session_id}` | `Portfolio` |
| `orders.list` | `{session_id, status?}` | `{orders: [...]}` |
| `fills.list` | `{session_id, since?}` | `{fills: [...]}` |
| `backtest.run` | `{session_id, bars: [{symbol, bar}], orders_script?}` | `{metrics: Metrics, fills, marks}` |
| `replay.load` | `{path}` — replays an event log and returns the final state | `Portfolio` |

Events (engine → gateway, JSON-RPC notifications):
`fill {session_id, order_id, symbol, side, qty_micro, price_micro, t, commission_micro}`,
`reject {session_id, order_id, reason}`, `mark {session_id, t, equity_micro, cash_micro, positions: [...]}`.

Types: `Portfolio {cash_micro, equity_micro, positions: [{symbol, qty_micro, avg_cost_micro, mark_micro, unrealized_micro}], realized_micro}`,
`Metrics {total_return, max_drawdown, sharpe, sortino, win_rate, trades, exposure}`.

Fill rules (v0): market orders fill at the bar's open of the *next* bar plus slippage;
limit orders fill if the bar's range crosses the limit, at the limit price; stops
trigger on the range then fill as market. No partial fills in v0. Shorting allowed
with 100% margin requirement. Rejections: insufficient cash/margin, unknown symbol,
qty <= 0, market closed (engine does not know calendars in v0; gateway filters).

Invariants the engine must test: cash + position value = equity at every mark;
sum of fills' signed quantities = position quantity; replaying the event log
reproduces the final portfolio exactly.

## 4. Gateway API (clients ↔ gateway)

Base `http://localhost:8787/api/v1`. JSON. Errors are `{error: {code, message}}`
with proper HTTP status. Auth: none in Phase 0–2 (localhost only).

| Method & path | Purpose |
|---|---|
| `GET /health` | `{status, engine: "up"\|"down", provider}` |
| `GET /symbols?q=` | search tradable symbols (from provider or static list) |
| `GET /bars/{symbol}?tf=1m\|5m\|1d&from=&to=` | cached historical bars |
| `GET /quote/{symbol}` | latest quote |
| `POST /sessions` | create a session (`{name, start_cash, mode: "backtest"\|"paper", start_time, seed}`) |
| `GET /sessions`, `GET /sessions/{id}` | list / inspect |
| `POST /sessions/{id}/orders` | submit an order (proxied to engine) |
| `DELETE /sessions/{id}/orders/{order_id}` | cancel |
| `GET /sessions/{id}/portfolio` | current portfolio |
| `GET /sessions/{id}/fills` | fills |
| `POST /sessions/{id}/runs` | start a strategy run (`{strategy_id, version, symbols, tf}`) |
| `GET /runs/{id}` | run status + metrics |
| `GET /board`, `POST /board/cards`, `PATCH /board/cards/{id}` | kanban cards (strategy, column, owner, notes, metrics) |
| `GET /strategies`, `POST /strategies`, `GET /strategies/{id}/versions` | strategy source registry |
| `GET /game/profile`, `GET /game/leaderboard`, `GET /game/season` | game layer |

WebSocket `ws://localhost:8787/ws`. Client sends `{type: "subscribe", topics: [...]}`.
Topics: `quotes:{symbol}`, `bars:{symbol}:{tf}`, `session:{id}` (fills, marks, order
updates), `board`, `runs:{id}`. Server messages: `{type, topic, t, payload}`.

## 5. Strategy runner protocol (runner ↔ gateway)

The runner connects to `/ws`, subscribes to `bars:*` for the run's symbols, and
submits orders through `POST /sessions/{id}/orders`. The strategy SDK gives a
strategy this interface:

```python
class Strategy(Protocol):
    name: str
    version: str
    symbols: list[str]
    timeframe: Literal["1m", "5m", "1d"]
    def on_start(self, ctx: Context) -> None: ...
    def on_bar(self, ctx: Context, bar: Bar) -> None: ...   # ctx.buy(), ctx.sell(), ctx.portfolio, ctx.history(n)
    def on_fill(self, ctx: Context, fill: Fill) -> None: ...
    def on_stop(self, ctx: Context) -> None: ...
```

Strategy code is untrusted (the Trader writes it). The runner executes it in a
subprocess with: no network except the gateway URL, a CPU/time budget per bar,
an import allowlist (`math`, `statistics`, `collections`, `dataclasses`, `numpy`,
`pandas`, the SDK), and a read-only filesystem. Violations stop the run with a
`reject` recorded on the card.

## 6. MCP tool surface (`mcp/`)

Tool names are `namespace.verb`. Inputs/outputs are JSON Schema with
`additionalProperties: false`. Every tool is read-only unless marked **W**.

| Tool | Purpose |
|---|---|
| `market.search`, `market.bars`, `market.quote` | data lookups |
| `session.create` **W**, `session.get`, `session.portfolio`, `session.fills` | account |
| `order.submit` **W**, `order.cancel` **W** | paper orders only |
| `strategy.list`, `strategy.get`, `strategy.put` **W** (new version), `strategy.lint` | strategy source |
| `backtest.run` **W**, `run.get`, `run.metrics` | evaluation |
| `board.get`, `board.move` **W**, `board.note` **W** | kanban |
| `journal.query`, `journal.write` **W** | the Trader's structured journal |
| `game.profile`, `game.leaderboard` | game |

Resources: `trade://board`, `trade://sessions/{id}`, `trade://strategies/{id}@{v}`,
`trade://journal/recent`. Prompts: `post_mortem(run_id)`, `propose_strategy(brief)`.

## 7. The Trader: memory and journal

- **Identity**: own process in `trader/`, own system prompt (`trader/prompts/system.md`),
  own API key, model `claude-opus-5-5`, adaptive thinking, effort `high` for strategy
  writing and `medium` for routine reviews.
- **Journal** (structured, SQLite, written through `journal.write`): one row per
  *thesis* (before a run: hypothesis, expected edge, risk), one per *review* (after:
  outcome, metrics, what the Trader believes caused it, lesson, next change), and one
  per *trade note* when a fill is notable. Rows reference `run_id`, `strategy_id`,
  `version`, `card_id`.
- **Memory** (free-form, filesystem under `data/trader/memory/`, via the Anthropic
  memory tool `memory_20250818`): the Trader keeps `lessons.md`, `playbook.md`,
  per-symbol notes, and a `mistakes.md` it is told to reread before every proposal.
- **Learning loop**: `trader-review` runs after every run: load journal thesis →
  load run metrics and fills through MCP → write review row → update memory →
  optionally `strategy.put` a new version and `board.move` the card. The loop is
  bounded (one new version per review) and never auto-promotes to `Paper Live`
  without a human moving the card.
- **Separation**: the Trader's memory directory is mounted nowhere else. Nothing in
  memory or journal is executed. The dev Claude Code session must not read the
  Trader's memory as instructions; it may inspect it as data to debug.

## 8. Data model (SQLite, owned by the gateway)

`sessions(id, name, mode, start_cash_micro, start_time, seed, created_at, closed_at)`
`orders(id, session_id, client_id, symbol, side, qty_micro, type, limit_micro, stop_micro, tif, status, reason, created_at)`
`fills(id, session_id, order_id, symbol, side, qty_micro, price_micro, commission_micro, t)`
`marks(session_id, t, equity_micro, cash_micro, positions_json)`
`strategies(id, name, owner: 'human'|'trader', created_at)`
`strategy_versions(strategy_id, version, source, sha256, created_by, created_at, lint_json)`
`runs(id, session_id, strategy_id, version, symbols_json, tf, status, metrics_json, started_at, ended_at)`
`cards(id, strategy_id, column, position, notes, created_at, updated_at)`
`card_events(card_id, t, actor, from_column, to_column, note)`
`journal(id, kind: 'thesis'|'review'|'trade_note', run_id, strategy_id, version, card_id, body_json, created_at)`
`game_profile(actor, xp, level, achievements_json)` · `seasons(id, starts, ends)` · `season_scores(season_id, actor, strategy_id, score)`
`bars(symbol, tf, t, o, h, l, c, v)` with index `(symbol, tf, t)`.
`events(session_id, seq, t, kind, payload_json)` is the engine's replay log mirror.

## 9. Local development topology

| Process | Port | Started by |
|---|---|---|
| gateway | 8787 | `make gateway-run` / `make dev` |
| engine | stdio | gateway |
| web (Vite) | 5173 | `make web-dev` / `make dev` |
| mcp (http) | 8788 | `make mcp-run` (stdio mode via `make mcp-stdio`) |
| strategy runner | — | gateway on `POST /runs`, or `make strategies-run` |
| trader | — | `make trader-run` (propose) / `make trader-review` (post-mortem) |

Runtime data under `./data` (gitignored): `trade.db`, `bars/`, `events/`, `trader/memory/`.

## 10. Game layer

- Actors: `human` and `trader`. Both have XP, level, achievements.
- XP sources: complete a backtest (+10), write a thesis before a run (+15), write a
  review after (+25), move a card to `Review` with metrics (+20), beat benchmark
  (SPY buy-and-hold) over a season (+200).
- Seasons are calendar months; `season_scores` ranks strategies by risk-adjusted
  return; the leaderboard shows human vs Trader.
- Achievements are data (`gateway/game/achievements.toml`), not code.

## 11. Security posture

- Localhost only; no auth in early phases; the gateway binds `127.0.0.1`.
- Provider keys read from env, never logged. Requests to providers are rate-limited
  and cached.
- Strategy sandbox as in §5. MCP `**W**` tools validate inputs with schemas and
  reject anything that is not a paper session.
- The Trader's outputs are data. The MCP server never executes strings it receives.

## 12. Decisions

See `docs/adr/`. ADR 0001 language split, ADR 0002 MCP-only AI boundary,
ADR 0003 paper money only, ADR 0004 chief/worker worktree workflow,
ADR 0005 no hosted CI.
