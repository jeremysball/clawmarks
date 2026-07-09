#!/bin/bash
# Idempotent training-environment setup for a fresh CLAWMARKS LoRA pod.
# Each step checks its own marker under /workspace/.setup_markers and skips if already done,
# so re-running this against a pod that already has the venv/checkpoint/kohya_ss present
# (e.g. one built on a persistent volume) finishes in seconds instead of minutes.
set -uo pipefail
MARKERS=/workspace/.setup_markers
mkdir -p "$MARKERS"

CIVITAI_MODEL_ID=889818
CIVITAI_TOKEN="${CIVITAI_TOKEN:?CIVITAI_TOKEN must be set in the environment}"
OUTLIER_IMAGE=Fg7u1FyXEAE5d_x

step() { echo "=== $1 ==="; }

if [ ! -f "$MARKERS/uv.done" ]; then
  step "installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
  touch "$MARKERS/uv.done"
else
  step "uv already installed, skipping"
fi
export PATH="$HOME/.local/bin:$PATH"

if [ ! -f "$MARKERS/venv.done" ]; then
  step "creating venv with pinned torch/xformers"
  cd /workspace
  uv venv venv --python 3.11
  source venv/bin/activate
  uv pip install torch==2.4.1 --index-url https://download.pytorch.org/whl/cu124
  uv pip install torchvision==0.19.1 --index-url https://download.pytorch.org/whl/cu124
  uv pip install xformers==0.0.28.post1 --no-deps --index-url https://download.pytorch.org/whl/cu124
  touch "$MARKERS/venv.done"
else
  step "venv already set up, skipping"
fi
source /workspace/venv/bin/activate

if [ ! -f "$MARKERS/kohya.done" ]; then
  step "cloning kohya_ss and installing requirements"
  cd /workspace
  git clone --depth 1 https://github.com/kohya-ss/sd-scripts.git kohya_ss
  cd kohya_ss
  uv pip install -r requirements.txt
  touch "$MARKERS/kohya.done"
else
  step "kohya_ss already present, skipping"
fi

if [ ! -f "$MARKERS/checkpoint.done" ]; then
  step "downloading Illustrious base checkpoint"
  mkdir -p /workspace/models
  curl -L "https://civitai.com/api/download/models/${CIVITAI_MODEL_ID}?token=${CIVITAI_TOKEN}" \
    -o /workspace/models/illustrious_v0.1.safetensors
  touch "$MARKERS/checkpoint.done"
else
  step "base checkpoint already downloaded, skipping"
fi

if ! command -v unzip &> /dev/null; then
  step "installing unzip"
  apt-get update -qq && apt-get install -y -qq unzip > /dev/null
fi

if [ ! -f "$MARKERS/dataset.done" ]; then
  step "extracting dataset, outlier image split into its own lower-repeat folder"
  set -e
  mkdir -p /workspace/training/img/10_trentbuckle /workspace/training/img/3_trentbuckle
  cd /workspace
  unzip -o -q clawmarks-dataset.zip -d /workspace/dataset_raw
  mv /workspace/dataset_raw/${OUTLIER_IMAGE}.jpg /workspace/dataset_raw/${OUTLIER_IMAGE}.txt \
    /workspace/training/img/3_trentbuckle/
  mv /workspace/dataset_raw/*.jpg /workspace/dataset_raw/*.txt /workspace/training/img/10_trentbuckle/
  rmdir /workspace/dataset_raw
  echo "10_trentbuckle: $(ls /workspace/training/img/10_trentbuckle/*.jpg | wc -l) images"
  echo "3_trentbuckle:  $(ls /workspace/training/img/3_trentbuckle/*.jpg | wc -l) images"
  touch "$MARKERS/dataset.done"
  set +e
else
  step "dataset already extracted, skipping"
fi

step "GPU check"
nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv

step "ready"
echo "train_data_dir = /workspace/training/img"
echo "base checkpoint = /workspace/models/illustrious_v0.1.safetensors"
echo "venv = /workspace/venv (activate with: source /workspace/venv/bin/activate)"
echo "kohya_ss = /workspace/kohya_ss"
