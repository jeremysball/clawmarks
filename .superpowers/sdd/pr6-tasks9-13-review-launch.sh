#!/usr/bin/env bash
set -euo pipefail
PROMPT="/workspace/trent-phase1-worktree/.superpowers/sdd/pr6-tasks9-13-review-prompt.md"
REPORT="/workspace/trent-with-smart-prompts/.superpowers/sdd/pr6-tasks9-13-review-report.md"

cd /workspace/trent-phase1-worktree
actual_branch="$(git rev-parse --abbrev-ref HEAD)"
if [ "$actual_branch" != "preference-classifier-phase-1" ]; then
  echo "ABORT: worktree is on branch '$actual_branch', expected preference-classifier-phase-1" >&2
  exit 1
fi

opencode run \
  --dir /workspace/trent-phase1-worktree \
  --dangerously-skip-permissions \
  --model opencode-go/glm-5.2 \
  --print-logs \
  -f "$PROMPT" \
  -- "Read the attached review brief in full — it is your complete instructions, including the
git range, the file with the pre-generated diff, the reference plan sections, the review focus
areas, the read-only rule (including the explicit warning not to touch the live
notes/uncanny_sweep* data directories), and the output format. Perform the review. Write your
complete review to $REPORT. Stop when done."
