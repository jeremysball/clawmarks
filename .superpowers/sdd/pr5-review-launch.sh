#!/usr/bin/env bash
set -euo pipefail
PROMPT="/workspace/trent-clawmarks-worktree/.superpowers/sdd/pr5-review-prompt.md"
REPORT="/workspace/trent-with-smart-prompts/.superpowers/sdd/pr5-review-report.md"

cd /workspace/trent-clawmarks-worktree
actual_branch="$(git rev-parse --abbrev-ref HEAD)"
if [ "$actual_branch" != "clawmarks-package-transition-wt" ]; then
  echo "ABORT: worktree is on branch '$actual_branch', expected clawmarks-package-transition-wt" >&2
  exit 1
fi

opencode run \
  --dir /workspace/trent-clawmarks-worktree \
  --dangerously-skip-permissions \
  --model opencode-go/glm-5.2 \
  --print-logs \
  -f "$PROMPT" \
  -- "Read the attached review brief in full — it is your complete instructions, including the
git range, the file with the pre-generated diff, the reference spec/plan docs, the review focus
areas, the read-only rule, and the output format. Perform the review. Write your complete review
to $REPORT. Stop when done."
