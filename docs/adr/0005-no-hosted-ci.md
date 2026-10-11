# ADR 0005 — No hosted CI; the chief's review is the merge gate

Status: Accepted (2026-10-11)

## Context
GitHub Actions on this private repo is billed against the owner's account, and
the owner declined to pay for it. Every change already passes through a chief
review that runs the same `make check` and `make test` targets a CI job would.

## Decision
No GitHub Actions workflows in the repo, and Actions is disabled in the repo
settings. The merge gate is the chief procedure in `docs/WORKFLOW.md` §3.5,
executed with `scripts/review-branch.sh <branch> <scopes> <worktree>`, which runs
the component check/test targets in the worker's worktree before `--no-ff` merge.
Component `CLAUDE.md` files do not document CI setup.

## Consequences
- A red `main` can only come from a skipped or dishonest review; the chief must
  run the targets, not trust the worker's report.
- Nothing runs on push. Contributors without the chief flow run `make check &&
  make test` locally before pushing a branch.
- If hosted CI is wanted later, re-add a workflow and supersede this ADR.
