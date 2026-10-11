#!/usr/bin/env bash
# Chief review helper (docs/WORKFLOW.md §3.5).
#   scripts/review-branch.sh <branch> <scope-dir>[,<scope-dir>...] [worktree-path]
# Prints commits and diff stat, checks every commit for Conventional subject,
# 72-char limit, attribution footer, and out-of-scope files, scans the diff for
# forbidden paths and secret-looking strings, and (with a worktree) runs the
# component check/test targets there. Exit 1 on any hard failure.
set -u
BR="${1:?branch}"; SCOPES="${2:?scope dirs, comma separated}"; WT="${3:-}"
git fetch -q origin
echo "== commits (origin/main..$BR) =="; git log --oneline --no-merges "origin/main..$BR"
echo; echo "== diff stat =="; git diff --stat "origin/main...$BR" | tail -n 30
echo; echo "== rule checks =="
fail=0; IFS=, read -ra sc <<<"$SCOPES"
for sha in $(git rev-list --reverse --no-merges "origin/main..$BR"); do
  subj=$(git log -1 --format=%s "$sha"); body=$(git log -1 --format=%B "$sha")
  echo "$subj" | grep -qE '^(feat|fix|docs|test|refactor|perf|build|ci|chore)\([a-z-]+\): .+' || { echo "  [x] ${sha:0:7} non-conventional subject: $subj"; fail=1; }
  [ "${#subj}" -le 72 ] || { echo "  [x] ${sha:0:7} subject longer than 72 chars"; fail=1; }
  echo "$body" | grep -q 'Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>' || { echo "  [x] ${sha:0:7} missing attribution footer"; fail=1; }
  for f in $(git diff-tree --no-commit-id --name-only -r "$sha"); do
    ok=0; for s in "${sc[@]}"; do case "$f" in "$s"/*) ok=1 ;; esac; done
    [ "$ok" = 1 ] || echo "  [!] ${sha:0:7} touches out-of-scope file: $f"
  done
done
if git diff --name-only "origin/main...$BR" | grep -E '^(data/|\.worktrees/)|(^|/)\.env$|(^|/)(node_modules|target|_build|\.venv|dist)/' ; then echo "  [x] forbidden paths in diff"; fail=1; fi
if git diff "origin/main...$BR" | grep -nE '^\+.*(sk-ant-[A-Za-z0-9_-]{8,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|gho_[A-Za-z0-9]{30,})' ; then echo "  [x] secret-looking string added"; fail=1; fi
echo "rule checks: $([ "$fail" = 0 ] && echo PASS || echo FAIL)"
if [ -n "$WT" ]; then
  echo; echo "== component checks in $WT =="
  for s in "${sc[@]}"; do
    if [ -f "$WT/$s/Makefile" ]; then
      (cd "$WT" && make "$s-check" && make "$s-test") || { echo "  [x] $s check/test failed"; fail=1; }
    else echo "  [-] $s has no Makefile"; fi
  done
fi
exit "$fail"
