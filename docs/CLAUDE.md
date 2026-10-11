# docs/ — CLAUDE.md

Inherits the root `CLAUDE.md`. This directory holds the binding contracts.

## What lives here
- `ARCHITECTURE.md` — component boundaries, protocols, schemas, ports. The source
  of truth; component CLAUDE.md files restate, never contradict.
- `WORKFLOW.md` — the chief/worker/worktree procedure with exact commands.
- `adr/NNNN-slug.md` — Architecture Decision Records. Immutable once `Accepted`;
  supersede with a new ADR instead of editing.

## Rules
- A protocol change and its doc change ship in the same commit (`docs(<scope>): …`
  if docs-only, otherwise the feature commit updates docs too).
- ADR format: Title, Status (Proposed/Accepted/Superseded by NNNN), Context,
  Decision, Consequences. Keep each under 80 lines.
- Prose: short sentences, tables for anything with more than two attributes, no
  marketing language. Commands go in fenced blocks and must have been run.
- Diagrams are ASCII in Markdown so they diff.
- Never document a command that does not exist yet without a "(planned)" marker.

## Commands
```bash
make docs-check   # markdown lint + link check (planned until web/ tooling exists)
```
