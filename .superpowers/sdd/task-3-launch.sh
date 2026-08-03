#!/usr/bin/env bash
set -euo pipefail
BRIEF="/workspace/trent-with-smart-prompts/.superpowers/sdd/task-3-brief.md"
REPORT="/workspace/trent-with-smart-prompts/.superpowers/sdd/task-3-report.md"
SESSION_ID="ses_0b63a61e6ffe1ObgjqtAcNs5Re"

opencode run \
  --continue \
  --session "$SESSION_ID" \
  --dir /workspace/trent-with-smart-prompts \
  --dangerously-skip-permissions \
  --model opencode-go/minimax-m3 \
  --print-logs \
  -f "$BRIEF" \
  -- "Task 2 is complete and was reviewed. Now implement Task 3.

Read the attached brief — it is your complete requirements. Implement ONLY this task.

When done:
1. Run the tests in the brief and verify they pass.
2. Commit exactly as the brief specifies.
3. Write a report to $REPORT with: status (DONE/DONE_WITH_CONCERNS/BLOCKED), git log --oneline output, test command and full output, any concerns.
4. Stop."
