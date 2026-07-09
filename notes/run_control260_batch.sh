#!/bin/bash
# Trains + samples control_260 replicates on one pod, sequentially. Usage: run_control260_batch.sh <pod> <name1> <name2> ...
set -e
POD="$1"
shift
cd /workspace/trent-with-smart-prompts
for name in "$@"; do
  echo "=== $name: training (pod $POD) ==="
  python3 notes/train_probe.py --name "$name" --max-train-steps 260 --pod "$POD"
  echo "=== $name: generating samples (pod $POD) ==="
  python3 notes/gen_samples.py --checkpoint "${name}_260" --pod "$POD"
done
echo "=== ALL DONE (pod $POD): $* ==="
