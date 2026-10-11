# Trade — Status (paused by the human on 2026-10-11, Phase 0)

The chief session is paused. No further merges happen until the human says continue.

## What is on `main` (reviewed and pushed)

| Area | State |
|---|---|
| Root `CLAUDE.md`, `docs/ARCHITECTURE.md`, `docs/WORKFLOW.md`, `docs/CLAUDE.md`, ADRs 0001–0005 | done |
| `.claude/settings.json` (allow/deny guardrails), `.claude/agents/*.md` (5 worker roles) | done |
| `.claude/panes/` (worker launcher, `paneflow up` spec, shared brief, brief template) | done |
| `scripts/review-branch.sh` (mechanical branch review), root `Makefile` (failure-propagating) | done |
| `gateway/` — Rust axum scaffold, `/api/v1/health`, error envelope, 5 tests, `gateway/CLAUDE.md` (339 lines) | **merged** |
| Hosted CI | removed by decision (ADR 0005); the chief review is the gate |
| GitHub repo | https://github.com/EvanGUTK/Trade, private, Actions disabled |

## The three running shells

They are **headless worker Claude sessions** (`claude -p …`), one per remaining
component, started by the chief as background processes because this Paneflow
session cannot open worker panes (see `docs/WORKFLOW.md` §6). Each works only in
its own worktree and branch and will push that branch when it finishes.

| Process cwd | Branch | Committed so far | Still doing |
|---|---|---|---|
| `.worktrees/engine` | `feat/engine-claude-md` | dune scaffold (Money module, JSON-RPC ping binary, tests) + `engine/CLAUDE.md` (349 lines) | final trims, rebase, push |
| `.worktrees/python` | `feat/python-claude-md` | `strategies/` scaffold, `mcp/` scaffold | `trader/` scaffold, then three CLAUDE.md files, push |
| `.worktrees/web` | `feat/web-claude-md` | Vite + React + TS scaffold (theme, API types, shell, tests) | `web/CLAUDE.md`, push |

Nothing they do touches `main`; they cannot (settings deny it, and they have no
merge step). Their branches are reviewed by the chief only after they report.

## Do you need to wait?

No. You can read, edit, or close other things. Two caveats:

- Keep this chief Claude session open until they finish. They are child processes
  of it; closing the session will most likely end them mid-turn. Committed work
  survives in the worktrees either way; uncommitted edits stay on disk but are not
  in git.
- To stop them deliberately: `pkill -f 'claude -p --permission-mode acceptEdits'`.
  To restart a stopped one later: rewrite its brief in `.claude/panes/briefs/<name>.md`
  to say "continue from the existing commits", then
  `.claude/panes/run-worker.sh <name> --headless`.

## When the human says continue

1. Review and merge in order: engine → web → python (`scripts/review-branch.sh`,
   then `docs/WORKFLOW.md` §3.5–3.6).
2. One chief commit stripping CI references from the new component CLAUDE.md
   files (their briefs predate ADR 0005).
3. Mirror the gateway worker's proposals into `docs/ARCHITECTURE.md` §4 (error
   codes, WS backpressure) and `.env.example` (`TRADE_ENGINE_BIN`).
4. Remove worktrees and branches; Phase 0 is then complete and Phase 1 starts.

## To see workers as Panes panes next time

Launch the chief as a "Claude Code (team)" pane, or start Paneflow with
`PANEFLOW_IPC_ORCHESTRATION=1` and run `paneflow up .claude/panes/workers.toml`.
