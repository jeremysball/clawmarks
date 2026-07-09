#!/bin/bash
# Trains + samples the remaining control_156 replicates needed to pool n=8, sequentially on pod 1.
set -e
cd /workspace/trent-with-smart-prompts
for name in controlD controlE controlF controlG controlH; do
  echo "=== $name: training ==="
  python3 notes/train_probe.py --name "$name" --max-train-steps 156 --pod 1
  echo "=== $name: generating samples ==="
  python3 notes/gen_samples.py --checkpoint "${name}_156" --pod 1
done
echo "=== ALL DONE: 5 more control replicates trained + sampled ==="
