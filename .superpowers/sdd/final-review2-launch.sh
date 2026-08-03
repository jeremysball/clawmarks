#!/bin/bash
set -euo pipefail
cd /workspace/trent-with-smart-prompts

MODEL_ARGS=(--model opencode-go/glm-5.2)
SESSION_ARGS=()
source "/home/node/.claude/skills/using-opencode/run.sh"

PROMPT="$(cat /workspace/trent-with-smart-prompts/.superpowers/sdd/final-review2-prompt.md)"

run_opencode "/workspace/trent-with-smart-prompts" "$PROMPT" "/workspace/trent-with-smart-prompts/.superpowers/sdd/review-9da9ad1..6c3056c.diff"
