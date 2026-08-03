#!/usr/bin/env bash
set -euo pipefail
BRIEF="/workspace/trent-with-smart-prompts/.superpowers/sdd/final-review-fix-brief.md"
REPORT="/workspace/trent-with-smart-prompts/.superpowers/sdd/final-review-fix-report.md"
SESSION_ID="ses_0b63a61e6ffe1ObgjqtAcNs5Re"

cd /workspace/trent-phase1-worktree
actual_branch="$(git rev-parse --abbrev-ref HEAD)"
if [ "$actual_branch" != "preference-classifier-phase-1" ]; then
  echo "ABORT: worktree is on branch '$actual_branch', expected preference-classifier-phase-1" >&2
  exit 1
fi

opencode run \
  --continue \
  --session "$SESSION_ID" \
  --dir /workspace/trent-phase1-worktree \
  --dangerously-skip-permissions \
  --model opencode-go/minimax-m3 \
  --print-logs \
  -f "$BRIEF" \
  -- "The final whole-branch review of Tasks 1-8 found two Important issues that must be fixed
before merge. Read the attached brief — it is your complete requirements. Fix both issues
exactly as described. Note: run tests with PYTHONPATH=src, e.g.
\`PYTHONPATH=src pytest -v\` (this worktree's src/ isn't installed into the shared venv the
same way the main directory's is).

When done:
1. Run the full suite and verify it passes.
2. Commit exactly as the brief specifies.
3. Write a report to $REPORT with: status (DONE/DONE_WITH_CONCERNS/BLOCKED), git log --oneline output, test command and full output, any concerns.
4. Stop."
