# ADR 0001 — Language split: OCaml engine, Rust gateway, Python AI/strategies, TypeScript web

Status: Accepted (2026-10-10)

## Context
Trade needs (a) a deterministic, exact, replayable simulation core, (b) a
long-running network hub with provider adapters and WebSocket fan-out, (c) code that
a Claude agent writes and rewrites frequently, plus the MCP and Anthropic SDKs,
(d) a dense trading UI. The human asked for OCaml, Rust "maybe", and Python.

## Decision
- `engine/` in OCaml 5 with dune: algebraic types for orders/fills/ledger, `result`
  at boundaries, property tests. Exposed only as a JSON-RPC-over-stdio child.
- `gateway/` in Rust with axum/tokio: owns persistence and all network I/O. If Rust
  slows the team down, a FastAPI gateway with the identical API is the fallback;
  the API in `docs/ARCHITECTURE.md` §4 is language-neutral for that reason.
- `strategies/`, `mcp/`, `trader/` in Python 3.14 with uv: official `anthropic` and
  `mcp` SDKs, and Python is the language an LLM writes trading logic in most
  reliably.
- `web/` in TypeScript/React 19 with Vite, lightweight-charts, dnd-kit.

## Consequences
- Three toolchains plus Node. Mitigated by a root Makefile and one worker per
  component.
- Money and quantities cross language boundaries as integer micro-units, never
  floats.
- Engine protocol is the one contract everyone depends on; it changes only with an
  ADR.
