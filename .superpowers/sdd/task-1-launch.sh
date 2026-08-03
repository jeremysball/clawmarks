#!/usr/bin/env bash
set -euo pipefail
BRIEF="/workspace/trent-with-smart-prompts/.superpowers/sdd/task-1-brief.md"
REPORT="/workspace/trent-with-smart-prompts/.superpowers/sdd/task-1-report.md"

opencode run \
  --dir /workspace/trent-with-smart-prompts \
  --dangerously-skip-permissions \
  --model opencode-go/minimax-m3 \
  --print-logs \
  -f "$BRIEF" \
  -- "You are implementing a single task in a plan for the CLAWMARKS LoRA project (a Python package, src/clawmarks).

Read the attached brief — it is your complete requirements. Implement ONLY this task. Do not read or attempt other tasks.

When done:
1. Run the tests in the brief and verify they pass.
2. Commit exactly as the brief specifies (files listed, message format).
3. Write a report to $REPORT with: status (DONE/DONE_WITH_CONCERNS/BLOCKED), git log --oneline output, test command and full output, any concerns.
4. Stop. Write nothing after the report."
