# Trade — Handoff (written 2026-10-11 by the chief at the end of Phase 0)

You are reading this because you are the **chief**: the Claude Code session the human
opened in this repo (as a Claude Code team pane). You run on Claude Fable 5.1 and only
orchestrate. Read, in order: root `CLAUDE.md` (all of it; §5 "Models" is the human's
standing policy), `docs/WORKFLOW.md`, then this file. Then confirm to the human what you
are about to do before spawning anything.

## 1. Model policy (binding, from the human)

| Role | Model | Effort | Notes |
|---|---|---|---|
| Chief (you) | `claude-fable-5-1` | — | orchestration only: briefs, worktrees, review, merge |
| Workers | `claude-sonnet-5-5` | `high` | the base model for every component task |
| Reviewer (checking worker code / merges) | `claude-opus-5-5` | default | `.claude/agents/reviewer.md`, read-only |
| Hard feature | `claude-opus-5-5` | `xhigh` | cross-component, protocol-changing, or failed twice on Sonnet; say why in the brief |

Agent tool: `model: "sonnet"`, `effort: "high"`. Pane/headless: `.claude/panes/run-worker.sh`
already passes `--model claude-sonnet-5-5 --effort high` (override with `WORKER_MODEL`, `WORKER_EFFORT`).

## 2. State of `main` (all reviewed, all pushed, `make check && make test` green)

| Component | What exists | Tests | CLAUDE.md |
|---|---|---|---|
| `engine/` (OCaml) | dune project; `Money` (int64 micro, checked), `Protocol` (JSON-RPC codec, error codes), `Rpc` (`ping`); stdin/stdout binary | 17 | 349 lines |
| `gateway/` (Rust) | axum crate; `GET /api/v1/health`; `GatewayError` envelope; 404/405 fallbacks; localhost bind; graceful shutdown | 5 | 339 lines |
| `strategies/` (Python) | pydantic wire models; `Strategy`/`Context` protocols; `indicators.sma`; `RecordingContext`; SMA-cross example; CLI stub | 13 | 272 lines |
| `mcp/` (Python) | `MCPServer("trade")` with `strict_tool` registration; `health` tool; stdio + streamable-HTTP | 6 | 242 lines |
| `trader/` (Python) | settings (`claude-opus-5-5` default); system prompt as package data; traversal-safe `MemoryStore`; planned-flow CLI stubs; no API calls | 19 | 267 lines |
| `web/` (TS) | Vite 8 + React 19 + TS 6; theme tokens; API types with `Micro`; three-column shell; health pill; proxy config | 10 | 347 lines |
| repo | root `CLAUDE.md`, `docs/ARCHITECTURE.md`, `docs/WORKFLOW.md`, ADRs 0001–0005, `.claude/` (settings, 5 agents, panes launcher + spec), `scripts/review-branch.sh`, `.mcp.json`, `.env.example` | — | — |

Decisions tonight: no hosted CI (ADR 0005, Actions disabled; the review is the gate);
the model policy above; rebase only before a worker's first push (`WORKFLOW.md` §4.4).
Accepted nits: three commit subjects of 74 chars on merged branches. `make dev` is a
placeholder until Phase 1.

## 3. How Phase 0 actually ran (so you can do better)

The four workers ran **headless** (`claude -p` in the background) because the chief's
pane was a plain `claude` pane: the Agent tool cannot open panes there, and `paneflow up`
needs Paneflow started with `PANEFLOW_IPC_ORCHESTRATION=1`. If the human opened you as a
Claude Code team pane, try the Agent tool first (one small worker, `model: "sonnet"`,
`effort: "high"`); if it opens a pane, use it for everything. Otherwise
`paneflow up .claude/panes/workers.toml` if the orchestration flag is set, else headless.
Details: `WORKFLOW.md` §6, `.claude/panes/README.md`.

The chief/worker git protocol worked end to end: 4 worktrees, 13 worker commits, 4
`--no-ff` merges, every branch checked with `scripts/review-branch.sh` plus a full read
of each CLAUDE.md. Workers were honest in their reports and found real defects in the
chief's files (Makefile failure masking, rebase-after-push rule, `.env.example` deny
rule); fold such proposals into docs promptly.

## 4. Phase 1 plan (root `CLAUDE.md` §10): "backtest end to end"

All four can run in parallel against the written contracts; integration is the last step.
Suggested briefs (one worker each, Sonnet 5.5 high; the engine ledger may qualify as a
hard feature if it stalls):

1. **engine** — `Qty`, `Clock`, `Order`, `Fill`, `Slippage` (none/bps/spread), `Ledger`,
   `Portfolio`, `Session`; methods `session.create/close`, `market.bar`, `order.submit/cancel`,
   `portfolio.get`, `orders.list`, `fills.list`, `backtest.run`; notifications `fill`,
   `reject`, `mark`; `Metrics`; qcheck invariants. Contract: `ARCHITECTURE.md` §3 + `engine/CLAUDE.md` §5–§6.
2. **gateway** — `config.rs`, `db/` + `0001_init.sql`, `providers/yahoo.rs` history + bar
   cache, `engine/` supervisor + rpc, routes `symbols bars quote sessions orders`, WS hub
   with `bars:* quotes:* session:*`, health reporting real state. Contract: §4, §8, `gateway/CLAUDE.md`.
3. **strategies** — `runner/` (WS + REST client, run loop), `sandbox/` (guest, allowlist,
   budgets, RO fs), `lint.py` (S001–S008), golden tests. Contract: §5, `strategies/CLAUDE.md` §5–§7.
4. **web** — chart (`/bars`, `bars:` topic, timeframe switch, fill markers), watchlist with
   live quotes, order ticket, positions/orders/fills, `ws.ts`, `market/session/ui` slices.
   Contract: §4, `web/CLAUDE.md` §5, §7, §8.
5. **integration** (chief, or one Opus xhigh worker if it is hard) — `make dev` via
   process-compose or a script, a recorded Yahoo fixture, one backtest of the SMA example
   through gateway → engine, visible in the web chart. Definition of Phase 1 done.

`mcp/` and `trader/` are Phase 2 (their CLAUDE.md §12 / §12 list the deliverables).

## 5. Open items for the human

- Provider: Yahoo history needs no key. Alpaca/Polygon/Finnhub keys go in `.env` when wanted.
- The repo is private; Actions is off. Making it public is the human's call.
- `web/` wants a tablet drawer and Playwright smoke in Phase 3; no decision needed now.

## 6. First five minutes as the new chief

1. `git status -sb && git log --oneline -8 && git worktree list` (expect clean, `main`, no worktrees).
2. `make check && make test` (expect green; takes a minute; engine needs the opam `default` switch, which the Makefile handles).
3. Read `CLAUDE.md` §5 "Models" and `WORKFLOW.md` §3.
4. Tell the human which launch mode you are in (team pane / `paneflow up` / headless) and which Phase 1 briefs you propose to send.
5. Provision worktrees and spawn.
