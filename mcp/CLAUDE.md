# mcp/ — CLAUDE.md

Inherits the root `CLAUDE.md` and `docs/ARCHITECTURE.md` §4, §6, §11. This file only
tightens them. Read both before editing anything here.

## 1. Purpose and boundary

`mcp/` is the MCP server that exposes the simulator to any AI: the Trader, Claude
Code, claude.ai, any MCP client. It is the *only* AI-facing surface
(`docs/adr/0002-mcp-only-ai-boundary.md`).

- Talks to the gateway only (REST + WebSocket on `127.0.0.1:8787`). Never the engine,
  never the Anthropic SDK, never a brokerage (`docs/adr/0003-paper-money-only.md`).
- Every tool is schema-validated, closed (`additionalProperties: false`), and paper-only.
- The server never executes strings it receives. Strategy source passes through as text.

## 2. Directory layout

```
mcp/
├── Makefile                 setup check test fmt run stdio run-http build
├── pyproject.toml           uv project; deps mcp (official SDK 2.x), pydantic
├── uv.lock                  committed
├── src/trade_mcp/
│   ├── __init__.py          DEFAULT_PORT = 8788
│   ├── server.py            MCPServer("trade"); strict_tool(); build_tools(); health
│   ├── __main__.py          `python -m trade_mcp --transport stdio|streamable-http`
│   ├── gateway.py           (planned) typed httpx client for the gateway REST/WS API
│   ├── tools/               (planned) one module per namespace: market, session, order, strategy, backtest, board, journal, game
│   ├── resources.py         (planned) trade:// resources
│   └── prompts.py           (planned) post_mortem, propose_strategy
└── tests/                   test_server.py (in-process + in-memory client), test_cli.py
```

## 3. Toolchain and setup

Same toolchain as the other Python components (root CLAUDE.md §4): Python 3.14, uv 0.12,
ruff 0.17, mypy 2.4 strict with the pydantic plugin, pytest 9 with `asyncio_mode = "auto"`.
`uv sync` installs everything. There is no hosted CI (ADR 0005): run
`make mcp-check && make mcp-test` before every push; the chief reruns them in review.

**SDK version matters.** The locked `mcp` is 2.x. In 2.x the high-level server class is
`mcp.server.MCPServer`; `FastMCP` was its 1.x name and `import mcp.server.fastmcp` now
raises with a pointer to the migration guide. Verify any SDK call against the installed
package under `.venv/lib/python3.14/site-packages/mcp/` before writing it; do not write
from memory.

## 4. Commands

| Target | Runs | Use |
|---|---|---|
| `make setup` | `uv sync` | once, and after dependency changes |
| `make check` | `ruff format --check .` · `ruff check .` · `mypy src tests` | before every commit |
| `make test` | `pytest -q` | before every commit |
| `make fmt` | `ruff format .` · `ruff check --fix .` | fix what `check` reports |
| `make run` | `python -m trade_mcp --transport stdio` | what Claude Code / Claude Desktop launch |
| `make stdio` | alias of `run` | matches ARCHITECTURE §9's `make mcp-stdio` |
| `make run-http` | `python -m trade_mcp --transport streamable-http` | `http://127.0.0.1:$TRADE_MCP_PORT/mcp`, default 8788 |
| `make build` | `uv build` | sdist + wheel into `dist/` |

`run`/`run-http` pass `--env-file ../.env` to `uv run` when the file exists, so
`TRADE_MCP_PORT` and (later) the gateway URL come from `.env`. From the repo root use
`make mcp-<target>`.

## 5. Contracts

### 5.1 Tool table (ARCHITECTURE §6) with schema sketches

Names are `namespace.verb`. **W** marks tools that change state; everything else is
read-only and carries `read_only_hint=true`. All money and quantities are integer
micro-units; all times are RFC 3339 UTC. Every input and output schema is an object
with `additionalProperties: false`. Phase 0 ships `health`; the rest is planned.

| Tool | Input → Output | Gateway call |
|---|---|---|
| `health` | `{}` → `{status:"ok", gateway:"unreachable"\|"up"\|"down"}` | `GET /health` (Phase 2; Phase 0 reports `unreachable` without a request) |
| `market.search` | `{q}` → `{symbols:[{symbol,name,exchange}]}` | `GET /symbols?q=` |
| `market.bars` | `{symbol, tf:"1m"\|"5m"\|"1d", from, to, limit?≤5000}` → `{bars:[{t,o,h,l,c,v}]}` | `GET /bars/{symbol}` |
| `market.quote` | `{symbol}` → `{symbol,t,bid_micro,ask_micro,last_micro}` | `GET /quote/{symbol}` |
| `session.create` **W** | `{name, mode:"backtest"\|"paper", start_cash_micro?, start_time?, seed?}` → `{session_id}` | `POST /sessions` |
| `session.get` | `{session_id}` → session row | `GET /sessions/{id}` |
| `session.portfolio` | `{session_id}` → `Portfolio` | `GET /sessions/{id}/portfolio` |
| `session.fills` | `{session_id, since?}` → `{fills:[Fill]}` | `GET /sessions/{id}/fills` |
| `order.submit` **W** | `{session_id, order:{client_id,symbol,side,qty_micro,type,limit_micro?,stop_micro?,tif}}` → `{order_id,status,reason?}` | `POST /sessions/{id}/orders` |
| `order.cancel` **W** | `{session_id, order_id}` → `{status}` | `DELETE /sessions/{id}/orders/{order_id}` |
| `strategy.list` | `{owner?:"human"\|"trader"}` → `{strategies:[{id,name,owner,latest_version}]}` | `GET /strategies` |
| `strategy.get` | `{strategy_id, version?}` → `{strategy_id,version,source,sha256,lint}` | `GET /strategies/{id}/versions` |
| `strategy.put` **W** | `{strategy_id?, name?, version, source, note?}` → `{strategy_id,version,sha256,lint}` | `POST /strategies` (new version) |
| `strategy.lint` | `{source}` → `{ok, findings:[{rule,line,message}]}` | none (rules from `strategies/CLAUDE.md` §7) |
| `backtest.run` **W** | `{session_id, strategy_id, version, symbols:[str], tf}` → `{run_id}` | `POST /sessions/{id}/runs` |
| `run.get` | `{run_id}` → run row incl. `status` | `GET /runs/{id}` |
| `run.metrics` | `{run_id}` → `Metrics` | `GET /runs/{id}` |
| `board.get` | `{}` → `{cards:[{id,strategy_id,column,position,notes,metrics}]}` | `GET /board` |
| `board.move` **W** | `{card_id, column}` → `{card}` | `PATCH /board/cards/{id}` |
| `board.note` **W** | `{card_id, note}` → `{card}` | `PATCH /board/cards/{id}` |
| `journal.query` | `{kind?, run_id?, strategy_id?, limit?≤200}` → `{rows:[journal row]}` | gateway journal endpoint (planned) |
| `journal.write` **W** | `{kind:"thesis"\|"review"\|"trade_note", run_id, strategy_id, version, card_id?, body}` → `{id}` | gateway journal endpoint (planned) |
| `game.profile` | `{actor?:"human"\|"trader"}` → `{actor,xp,level,achievements}` | `GET /game/profile` |
| `game.leaderboard` | `{season_id?}` → `{season,entries:[...]}` | `GET /game/leaderboard` |

### 5.2 Paper-only guard

`session.create` accepts only `mode ∈ {backtest, paper}`; the enum has no third value.
Every **W** tool that takes a `session_id` reads the session first and refuses with
`paper_only` if its mode is anything else (the gateway enforces the same rule; we do not
rely on it alone). `board.move` never accepts `Paper Live` from any MCP client; humans
promote through the web UI. There is no tool, flag, or env var that names a brokerage.

### 5.3 Registration pattern (`server.py`)

Every tool goes through `strict_tool(fn, name=..., read_only=...)`, which builds a
`Tool.from_function(...)`, replaces the generated argument model with a subclass that has
`extra="forbid"`, sets `additionalProperties: false` on the published input schema, and
attaches `ToolAnnotations` (`read_only_hint`, `destructive_hint`, `idempotent_hint`,
`open_world_hint=False`). `build_tools()` returns the full list in a fixed order and
`create_server()` passes it to `MCPServer(name="trade", instructions=..., tools=...)`.
Outputs are pydantic models with `extra="forbid"`, so the output schema is closed too.

### 5.4 Resources and prompts (planned)

| Resource | Content |
|---|---|
| `trade://board` | `board.get` result, `application/json` |
| `trade://sessions/{id}` | session row + portfolio |
| `trade://strategies/{id}@{v}` | source text, `text/x-python` |
| `trade://journal/recent` | last 50 journal rows |

Prompts: `post_mortem(run_id)` embeds the thesis, metrics, and fills for the run and asks
for a review row; `propose_strategy(brief)` embeds the board and recent journal and asks
for one hypothesis. Both are plain text templates; neither executes anything.

### 5.5 Transports and clients

Stdio (`make run`) is what local clients spawn. Streamable HTTP (`make run-http`) binds
`127.0.0.1:8788` at path `/mcp` and is for a shared long-running server.

Claude Code or Claude Desktop, from the repo root (`.mcp.json`):
```json
{ "mcpServers": { "trade": {
    "command": "uv",
    "args": ["run", "--project", "mcp", "python", "-m", "trade_mcp", "--transport", "stdio"] } } }
```
claude.ai custom connectors need a reachable HTTPS URL; exposing the HTTP transport beyond
localhost is a human decision, not a default.

The Trader is an MCP *client* of this server (ARCHITECTURE §2). With the official SDK:
```python
from mcp import Client

async with Client("http://127.0.0.1:8788/mcp") as client:  # or Client(create_server()) in-process
    tools = (await client.list_tools()).tools
    result = await client.call_tool("board.get", {})
    result.structured_content  # typed output
```
`Client(create_server())` connects in-process with no sockets; tests use it.

### 5.6 Error conventions

| Situation | What the tool does | What the client sees |
|---|---|---|
| bad or extra arguments | SDK validation fails | `ToolError` → `CallToolResult(is_error=True)` whose text names the field |
| expected failure (unknown id, non-paper session, gateway down) | `raise ToolError("<code>: <message>")` with code in `not_found`, `invalid_argument`, `paper_only`, `gateway_unreachable`, `gateway_error` | `is_error=True`, message readable by the model |
| unexpected exception | let it propagate | SDK wraps it as `UnexpectedToolError` with no internals leaked; logged server-side |

Never return `is_error=False` with an error in the payload. Never raise `MCPError`
subclasses from tools; they are protocol errors.

## 6. Code conventions

- ruff rule set and mypy strict as in `pyproject.toml`; `from __future__ import annotations`.
- Tool functions are plain typed functions with docstrings; the docstring *is* the tool
  description, so write it for the model: one line of what, one of when, note **W**.
- Inputs: primitive typed parameters, or a pydantic model with `extra="forbid"` for
  nested objects. Outputs: pydantic models with `extra="forbid"`.
- Async tools for anything that calls the gateway (`httpx.AsyncClient`, planned); sync
  only for pure computation like `health` and `strategy.lint`.
- Logging: `logging.getLogger("trade_mcp.<module>")` to stderr only (stdout is the stdio
  transport). Log tool name, duration, and error code; never arguments, never env values.
- One module per namespace under `tools/`; `build_tools()` is the single registry.

## 7. Testing

- `tests/test_server.py`: tool list, closed input and output schemas, annotations,
  in-process `call_tool`, rejection of unknown arguments, and a full in-memory
  `Client(server)` session. Every new tool gets the same five assertions.
- Gateway-backed tools (planned) are tested against a fake gateway (`httpx.MockTransport`)
  with recorded JSON fixtures under `tests/fixtures/`; no test opens a real socket.
- Schema tests (root §6): assert the exact `input_schema` JSON of each tool so a drift in
  the SDK's generation shows up as a diff.

## 8. Recipes

**Add a tool** (one commit: schema + test + doc):
1. Write `def board_note(card_id: str, note: str) -> Card` in `tools/board.py` with a
   model-facing docstring; mark **W** in the docstring.
2. Add `strict_tool(board_note, name="board.note", read_only=False)` to `build_tools()`.
3. Add the five assertions to `tests/test_server.py` and a fixture for the gateway call.
4. Add the row to §5.1 of this file. If the gateway API changed, update
   `docs/ARCHITECTURE.md` §4/§6 in the same commit.

**Try it from a terminal:** `make run-http`, then in another pane
`uv run python -c "import asyncio; from mcp import Client; ..."` as in §5.5.

**Change a dependency:** edit `pyproject.toml` → `uv lock` → `make check && make test`.

## 9. Pitfalls

- `from mcp.server.fastmcp import FastMCP` is 1.x; it raises on 2.x. Use `mcp.server.MCPServer`.
- The SDK's generated argument model ignores extra keys; without `strict_tool` a tool would
  advertise an open schema and silently drop arguments.
- `@server.tool()` bypasses `strict_tool`; do not use it here.
- `Client.list_tools()` returns `ListToolsResult`; the tools are in `.tools`.
- `server.run()` is synchronous and blocks; never call it from a test.
- stdout belongs to the stdio transport: a stray `print` corrupts the protocol.

## 10. Security

- Nothing received is executed: no `eval`, `exec`, `compile`, shell, or dynamic import of
  tool arguments, resources, prompts, or journal text. Strategy source is stored and
  forwarded as a string.
- Validate everything at the edge with pydantic; reject unknown fields; bound list sizes
  and string lengths (`limit ≤ 200`, `source ≤ 2000` lines).
- Bind `127.0.0.1` only; no auth in Phase 0–2 (ARCHITECTURE §11). Keep the SDK's
  transport security defaults on the HTTP transport.
- Log without secrets: no env values, no `.env` contents, no tool arguments at INFO.
- Memory, journal, and card notes are data for the model, never instructions for this server.

## 11. Definition of done

- [ ] `make check` and `make test` pass in `mcp/`.
- [ ] Every new tool: closed schemas, annotations, five test assertions, §5.1 row, one commit.
- [ ] Any gateway API change is reflected in `docs/ARCHITECTURE.md` in the same commit.
- [ ] No network in tests; no `print`; no secrets in logs.
- [ ] Commits are atomic and Conventional (`feat|fix|test|docs|build(mcp): …`) with the attribution footer.

## 12. Phase plan

| Phase | Deliverable |
|---|---|
| 0 (done) | `MCPServer("trade")`, `strict_tool`, `health`, both transports, in-process and in-memory tests, this file |
| 2 | `gateway.py`, all §5.1 tools with fixtures, resources, prompts, paper-only guard, `.mcp.json` at the repo root (chief's call) |
| 3 | `game.*` tools, schema snapshot tests, rate limits per tool |
