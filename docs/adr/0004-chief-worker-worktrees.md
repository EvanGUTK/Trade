# ADR 0004 — Chief/worker development with git worktrees and atomic commits

Status: Accepted (2026-10-10)

## Context
Trade is also a test bed for Panes (Paneflow) multi-agent development. Several Claude
agents work at once on different components and must not corrupt each other's state
or `main`.

## Decision
One chief session coordinates; each worker gets its own worktree under `.worktrees/`
and its own `feat/<scope>-<slug>` branch tracking `origin`. Workers rebase on
`origin/main` before every push and never force-push. Only the chief merges, with
`--no-ff`, after reviewing every commit. Commits are atomic and Conventional with
an attribution footer. Full procedure in `docs/WORKFLOW.md`.

## Consequences
- History reads as a sequence of reviewed merges, each containing small, buildable
  commits.
- Parallelism is bounded by component count; cross-cutting changes are chief work.
- Workers cannot accidentally see or edit each other's uncommitted files.
