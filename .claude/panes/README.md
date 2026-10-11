# .claude/panes — launching workers in Paneflow

Files:
- `run-worker.sh <name> [--headless]` — starts a worker Claude in `.worktrees/<name>` with `briefs/<name>.md` + `briefs/_common.md` as its prompt.
- `workers.toml` — `paneflow up` spec opening one interactive worker pane per component.
- `briefs/_common.md` — rules every worker gets (commit format, forbidden actions, report shape). Committed.
- `briefs/TEMPLATE.md` — skeleton the chief copies to `briefs/<name>.md` per task. Committed.
- `briefs/<name>.md` — the per-task brief. Gitignored (ephemeral).

Launch modes, gates, and monitoring: `docs/WORKFLOW.md` §6.
