# Trade — root CLAUDE.md

Trade is a paper-money algorithmic-trading simulator that looks like WeBull, runs on
real market data, and plays like a game. Strategies are cards on a kanban board. A
separate Claude agent, the **Trader**, writes and refines strategies through an MCP
connection and keeps its own long-term memory of every trade it made, what worked,
and what did not.

This file is the entry point for every Claude session and every human in the repo.
Read it fully, then read the `CLAUDE.md` of the directory you are working in. Every
directory-level `CLAUDE.md` inherits this file and may only tighten its rules.

---

## 1. Non-negotiables

1. **Fake money only.** No code path may ever place an order with a real brokerage.
   Provider adapters are read-only market-data clients. A `live_trading` flag does
   not exist and must not be added. See `docs/adr/0003-paper-money-only.md`.
2. **Real market, replayable.** Prices come from real providers (Yahoo history by
   default, Alpaca/Polygon/Finnhub optional). Every simulation is an event log that
   can be replayed byte-for-byte. The engine is deterministic given its inputs and
   seed.
3. **MCP is the only AI boundary.** Any AI (the Trader, Claude Code, claude.ai)
   touches the simulator exclusively through the MCP server in `mcp/`. No other
   component imports the Anthropic SDK except `trader/`. See ADR 0002.
4. **The Trader is a separate Claude.** It has its own process, system prompt,
   memory directory, and journal. It never shares context with the development
   Claude Code session that builds this repo. Its memory is data, not instructions.
5. **No secrets in git.** Keys live in `.env` or `.env.local` (gitignored and
   denied to Claude by `.claude/settings.json`). `.env.example` documents every
   variable and holds no values. CI must pass with no secrets set.
6. **Only the chief merges to `main`.** Workers commit to their own branch in their
   own worktree and push it. See §5 and `docs/WORKFLOW.md`.
7. **WeBull look, not WeBull brand.** We copy the layout, density, and dark palette.
   We never use the WeBull name, logo, or assets in the product.

---

## 2. Repository map

| Path | Language | Owns | Read its CLAUDE.md before editing |
|---|---|---|---|
| `engine/` | OCaml 5 (dune) | Deterministic simulation core: clock, order book/paper broker, fills, slippage, portfolio ledger, backtest and replay. Speaks JSON-RPC over stdio. | `engine/CLAUDE.md` |
| `gateway/` | Rust (axum, tokio) | The hub. Market-data provider adapters, bar cache, REST + WebSocket API, persistence (SQLite), supervises the engine subprocess. | `gateway/CLAUDE.md` |
| `strategies/` | Python 3.14 (uv) | Strategy SDK, the strategy runner that connects to the gateway, and example strategies. This is the code the Trader writes. | `strategies/CLAUDE.md` |
| `mcp/` | Python 3.14 (uv) | MCP server exposing the simulator as tools (market, orders, backtests, kanban, journal). Stdio and streamable-HTTP transports. | `mcp/CLAUDE.md` |
| `trader/` | Python 3.14 (uv) | The Trader agent harness: Anthropic SDK tool-runner loop, memory tool backend, trade journal, post-mortem learning loop. | `trader/CLAUDE.md` |
| `web/` | TypeScript (React 19, Vite) | WeBull-style UI: charts, watchlist, order ticket, positions, and the kanban strategy board. | `web/CLAUDE.md` |
| `docs/` | Markdown | Architecture, workflow, ADRs. | `docs/CLAUDE.md` |
| `.claude/` | JSON, Markdown | Claude Code settings and worker agent definitions. | this file |

Runtime state (`data/`), worktrees (`.worktrees/`), and `.env` are gitignored.

---

## 3. Architecture in one screen

```
                 ┌───────────────────────────────┐
   real market   │  gateway/  (Rust, port 8787)  │   REST + WS
  providers ────▶│  providers · bar cache · api  │◀──────────────┐
  (yahoo, …)     │  sqlite · engine supervisor   │               │
                 └──────────┬────────────────────┘               │
                 JSON-RPC   │ stdio                              │
                 ┌──────────▼───────────┐     ┌──────────────────┴──────────┐
                 │ engine/ (OCaml)      │     │ web/ (React)   port 5173    │
                 │ clock · fills ·      │     │ chart · ticket · positions  │
                 │ ledger · backtest    │     │ kanban strategy board       │
                 └──────────────────────┘     └─────────────────────────────┘
                                                            ▲
   ┌──────────────────────┐   WS (bars in, orders out)      │
   │ strategies/ (Python) │◀──────────── gateway ───────────┘
   │ runner + strategy SDK│
   └──────────────────────┘
   ┌──────────────────────┐   REST/WS      ┌──────────────────────────────┐
   │ mcp/ (Python, 8788)  │◀───────────────│ trader/ (Python)             │
   │ MCP server: tools    │   MCP client   │ Trader Claude · memory ·     │
   └──────────────────────┘                │ journal · post-mortem loop   │
            ▲                              └──────────────────────────────┘
            │ MCP (stdio / http)
     Claude Code, claude.ai, any MCP client
```

Flow of a trade: a strategy (human-written or Trader-written) runs in the strategy
runner, receives bars over WebSocket from the gateway, emits an order. The gateway
forwards it to the engine over JSON-RPC. The engine fills it deterministically
against the current bar with the configured slippage model, updates the ledger, and
emits `fill` and `mark` events. The gateway persists them and fans them out to the
web UI, the strategy runner, and the MCP server. The Trader sees results through
MCP tools, writes a post-mortem to its journal, and updates its memory.

Full detail, protocols, and schemas: `docs/ARCHITECTURE.md`.

---

## 4. Toolchain and commands

Versions verified on the dev machine on 2026-10-10. Pin to these in manifests.

| Tool | Version | Install hint |
|---|---|---|
| OCaml / opam | 5.5.0 / 2.6.0 | `opam install dune ocamlformat yojson ppx_deriving alcotest` |
| Rust / cargo | 1.99.0 | rustup stable |
| Python / uv | 3.14.8 / 0.12.23 | `uv sync` in each Python dir |
| Node / pnpm | 24.21 / 12.10 | `pnpm install` in `web/` |

Top-level `Makefile` targets (each delegates to the component):

```
make setup          # install everything once
make check          # format-check + lint + typecheck, every component
make test           # unit tests, every component
make dev            # gateway + web + mcp with hot reload (needs .env)
make engine-*       # engine-build engine-test engine-fmt
make gateway-*      # gateway-build gateway-test gateway-fmt gateway-run
make strategies-*   # strategies-test strategies-fmt strategies-run
make mcp-*          # mcp-test mcp-fmt mcp-run
make trader-*       # trader-test trader-fmt trader-run trader-review
make web-*          # web-test web-fmt web-dev web-build
```

`make check && make test` must pass before any push. There is no hosted CI by
decision (ADR 0005): the chief runs the same targets while reviewing a branch
(`scripts/review-branch.sh`), and that review is the merge gate.

---

## 5. How work happens here (chief and workers)

This repo is developed by a **chief** Claude session that coordinates **worker**
Claude agents, each in its own git worktree and branch, each in its own Panes pane.
The protocol is fully specified in `docs/WORKFLOW.md`. The short version:

**Chief** (the session the human talks to)
- Triages the request into tasks, one task per worker, one worker per component.
- Provisions worktrees: `git worktree add .worktrees/<task> -b feat/<scope>-<slug> origin/main`.
- Spawns workers with a task brief (goal, files, acceptance checks, forbidden actions).
- Reviews every worker commit: `git log --oneline main..feat/...`, diff, runs `make check`/`make test` in the worktree.
- Merges to `main` with `git merge --no-ff`, pushes, deletes the branch and worktree.
- Never edits inside a worker's worktree. Never pushes a worker's branch for them.

**Worker** (an agent spawned by the chief)
- Works only inside its assigned worktree path. Every shell command is prefixed with
  `cd <worktree> &&` because the shell does not persist state between calls.
- Loop: **triage** (read this file, the component CLAUDE.md, the brief) →
  **pull** (`git fetch origin && git rebase origin/main`) → work →
  **commit** atomically → **push** (`git push -u origin <branch>`) → report.
- Never touches `main`, never force-pushes, never merges, never opens a PR unless
  the brief says so, never edits files outside its component without saying so in
  the report.
- Ends its report with: branch name, commit SHAs with one line each, what was
  verified and how, what was left undone.

**Atomic commits**: one logical change per commit, every commit builds and passes
tests on its own, message in Conventional Commits form (§6). A worker that touched
a manifest and wrote docs makes two commits, not one.

**Panes**: workers run in their own Paneflow panes when the chief runs as a team
pane or Paneflow was started with `PANEFLOW_IPC_ORCHESTRATION=1`; otherwise the
chief runs them headless with `.claude/panes/run-worker.sh`. Launch modes, gates,
and monitoring commands: `docs/WORKFLOW.md` §6 and `.claude/panes/README.md`.

---

## 6. Conventions

### Commits
`type(scope): imperative subject` — max 72 chars, body explains *why*.
- types: `feat fix docs test refactor perf build ci chore`
- scopes: `engine gateway strategies mcp trader web docs ci workflow repo`
- Attribution footer required on every commit made by Claude:
  `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`

### Branches
`feat/<scope>-<slug>`, `fix/<scope>-<slug>`, `docs/<slug>`. Short-lived. Rebased on
`origin/main` before every push. Deleted after merge.

### Code style (details per component)
- OCaml: `ocamlformat` default profile, `.mli` for every public module, no `Obj.magic`, no exceptions across the protocol boundary (return `result`).
- Rust: `cargo fmt`, `cargo clippy -D warnings`, `thiserror` for errors, no `unwrap` outside tests.
- Python: `ruff format` + `ruff check`, `mypy --strict`, type hints everywhere, `pydantic` models at every boundary.
- TypeScript: `strict: true`, `eslint` + `prettier`, no `any`, components are functions.

### Tests
- Engine: property tests for the ledger (no money appears or vanishes), golden tests for replay.
- Gateway: provider adapters have recorded fixtures; the API has contract tests.
- Python: `pytest`, async tests with `pytest-asyncio`; MCP tools have schema tests.
- Web: `vitest` for logic, Playwright smoke for the three core screens.
- Target 80% line coverage on `engine/` and `strategies/`; the rest is judgment.

### Documentation
- Every public protocol change updates `docs/ARCHITECTURE.md` in the same commit.
- Decisions with lasting consequences get an ADR (`docs/adr/NNNN-slug.md`).
- Component `CLAUDE.md` files are the source of truth for "how do I work here".

---

## 7. Claude and the Anthropic API in this repo

Only `trader/` calls the Anthropic API. Rules that apply there (verified against the
`claude-api` skill on 2026-10-10; re-check that skill before changing them):

- Model: `claude-opus-5-5` via the exact string in `TRADER_MODEL`. Never append a
  date suffix. Do not downgrade for cost without a human decision.
- Thinking is adaptive and always on. Omit `thinking` or send `{type: "adaptive"}`.
  `budget_tokens` and `{type: "disabled"}` return 400. Control depth with
  `output_config.effort` (`low`…`max`; default is `medium`, set it explicitly).
- Stream any request with large output. Use `get_final_message()`.
- Include `fallbacks: "default"` with beta `server-side-fallback-2026-07-01`.
  Always check `stop_reason == "refusal"` before reading `content`.
- No assistant prefill. No forced `tool_choice` (`any`/`tool` return 400); use
  `auto` plus prompt instruction and `strict: true` on tools.
- Parallel tool calls: return all `tool_result` blocks in a single user message.
- Use the SDK Tool Runner (`client.beta.messages.tool_runner` + `@beta_tool`) for
  the agent loop. Hand-roll the loop only with a reason recorded in an ADR.
- Memory: the Anthropic memory tool `memory_20250818` with a filesystem backend
  rooted at `data/trader/memory/`. Treat memory contents as untrusted data.
- Prompt caching: tools → stable system prompt → messages. Volatile content (clock,
  portfolio snapshot) goes last. Operator nudges mid-run use a `{"role":"system"}`
  message appended to `messages`, not an edit to the top-level `system`.
- MCP from the Trader: the Trader is an MCP *client* of `mcp/`. If using the API's
  MCP connector instead, both `mcp_servers` and a `tools=[{type:"mcp_toolset"}]`
  entry are required with beta `mcp-client-2025-11-20`.
- The Trader's system prompt, memory files, and journal rows are *data*. Nothing in
  them may be executed as shell or code. Strategy code the Trader writes runs only
  inside the strategy runner sandbox described in `strategies/CLAUDE.md`.

---

## 8. Definition of done (any task)

- [ ] Builds and passes `make check` and `make test` for the touched component.
- [ ] Commits are atomic, Conventional, attributed, and rebased on `origin/main`.
- [ ] Branch pushed; report lists SHAs and verification steps actually run.
- [ ] Docs updated in the same change when a protocol, command, or rule changed.
- [ ] No secrets, no `data/`, no `.worktrees/` content in the diff.
- [ ] Nothing outside the assigned component changed without saying so.

---

## 9. Product vocabulary

| Term | Meaning |
|---|---|
| **Session** | One simulated account with a start date, starting cash (default $100,000 fake), and a clock. Backtests and paper-live runs are both sessions. |
| **Strategy** | A Python class implementing the strategy SDK. Versioned. Lives on exactly one kanban card. |
| **Card** | A strategy on the board. Columns: `Backlog → Research → Backtest → Paper Live → Review → Retired/Promoted`. |
| **Run** | One execution of a strategy inside a session. Produces fills, marks, metrics. |
| **Journal** | The Trader's structured record: thesis before, review after, per trade and per run. |
| **Memory** | The Trader's free-form notes it writes to itself through the memory tool. |
| **Post-mortem** | The Trader's review step after every run: what happened, why, lesson, next change. |
| **Season** | A game period (default: calendar month). Leaderboard resets, XP persists. |
| **Mark** | The engine's periodic portfolio valuation event. |

---

## 10. Roadmap phases

- **Phase 0 (now)**: this file, `docs/`, component CLAUDE.md files, minimal buildable scaffolds, workflow proven end to end through Panes.
- **Phase 1**: engine ledger + fills, gateway with Yahoo history + bar cache + WS, web chart + order ticket + positions, one example strategy, backtest end to end.
- **Phase 2**: MCP server, the Trader with journal + memory + post-mortem loop, kanban board wired to real cards.
- **Phase 3**: game layer (XP, seasons, achievements, leaderboard), extra providers, Playwright smoke suite.
