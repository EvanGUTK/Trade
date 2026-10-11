#!/usr/bin/env bash
# Launch a Trade worker Claude in its worktree with its brief as the prompt.
#   .claude/panes/run-worker.sh <name>             interactive (for a Paneflow pane)
#   .claude/panes/run-worker.sh <name> --headless  print mode, for background use
# Run from the MAIN checkout (.worktrees/ lives there). The chief must first run
#   git worktree add .worktrees/<name> -b feat/<scope>-<slug> origin/main
# and write .claude/panes/briefs/<name>.md (see TEMPLATE.md). See docs/WORKFLOW.md §6.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
NAME="${1:?usage: run-worker.sh <name> [--headless]}"
MODE="${2:-}"
WT="$ROOT/.worktrees/$NAME"
BRIEF="$ROOT/.claude/panes/briefs/$NAME.md"
COMMON="$ROOT/.claude/panes/briefs/_common.md"
[ -d "$WT" ] || { echo "no worktree at $WT"; exit 1; }
[ -f "$BRIEF" ] || { echo "no brief at $BRIEF"; exit 1; }
PROMPT="$(cat "$BRIEF"; echo; echo '---'; cat "$COMMON")"
TOOLS="Bash,Read,Write,Edit,Glob,Grep,Skill,ToolSearch"
MODEL="${WORKER_MODEL:-claude-sonnet-5-5}"   # root CLAUDE.md §5 "Models": workers on Sonnet 5.5
EFFORT="${WORKER_EFFORT:-high}"              # opus + xhigh only for a hard feature the chief names
cd "$WT" || exit 1
if [ "$MODE" = "--headless" ]; then
  exec claude -p --model "$MODEL" --effort "$EFFORT" --permission-mode acceptEdits --allowedTools "$TOOLS" --max-turns 250 --output-format text "$PROMPT" < /dev/null
fi
claude --model "$MODEL" --effort "$EFFORT" --permission-mode acceptEdits --allowedTools "$TOOLS" "$PROMPT"
echo; echo "[$NAME worker] claude exited ($?). Pane kept open for inspection."
exec bash
