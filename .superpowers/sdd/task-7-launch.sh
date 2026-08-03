#!/usr/bin/env bash
set -euo pipefail
BRIEF="/workspace/trent-with-smart-prompts/.superpowers/sdd/task-7-brief.md"
REPORT="/workspace/trent-with-smart-prompts/.superpowers/sdd/task-7-report.md"
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
  -- "Task 6 is complete and was reviewed. Now implement Task 7.

Read the attached brief — it is your complete requirements. Implement ONLY this task. Do not read or attempt other tasks.

When done:
1. Run the tests in the brief and verify they pass.
2. Commit exactly as the brief specifies (files listed, message format).
3. Write a report to $REPORT with: status (DONE/DONE_WITH_CONCERNS/BLOCKED), git log --oneline output, test command and full output, any concerns.
4. Stop."
