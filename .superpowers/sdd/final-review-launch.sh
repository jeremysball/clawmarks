#!/usr/bin/env bash
set -euo pipefail
PROMPT="/workspace/trent-with-smart-prompts/.superpowers/sdd/final-review-prompt.md"
REPORT="/workspace/trent-with-smart-prompts/.superpowers/sdd/final-review-report.md"

opencode run \
  --dir /workspace/trent-phase1-worktree \
  --dangerously-skip-permissions \
  --model opencode-go/glm-5.2 \
  --print-logs \
  -f "$PROMPT" \
  -- "Read the attached review brief in full — it is your complete instructions, including the
git range, the file with the pre-generated diff, the global constraints, and the read-only
rule. Perform the review. Write your complete review (Strengths, Issues, Recommendations,
Assessment) to $REPORT. Stop when done."
