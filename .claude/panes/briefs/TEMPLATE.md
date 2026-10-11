You are the **<component> worker** for Trade. You own `<component>/` only.

WORKTREE=/home/usaas/Projects/Panes/Trade/.worktrees/<name>
BRANCH=feat/<scope>-<slug>

## Step 1 — Triage
Read, in order: `CLAUDE.md` (root), `docs/ARCHITECTURE.md` (§… are yours), `<component>/CLAUDE.md`, `docs/WORKFLOW.md` §4 (follow exactly). Confirm `git status` is clean and `git branch --show-current` prints `<branch>`.

## Step 2 — <first logical change> (commit 1: `<type>(<scope>): <subject>`)
<exact files, behavior, and the commands that must pass>

## Step 3 — <second logical change> (commit 2)
<…>

## Step 4 — Push and report
`cd <WORKTREE> && git fetch origin && git rebase origin/main && make <component>-check && make <component>-test && git push -u origin <branch>`.
Forbidden: anything outside `<component>/`; <task-specific forbidden actions>.
