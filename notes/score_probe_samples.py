"""
Score every generated probe-sample image (notes/probe_samples/<name>_<steps>/im_*.png)
against the real-art DINOv2 centroid, for the probe-length calibration check (step 1).
Reports one mean centroid-similarity score per checkpoint, plus a probe-vs-full ranking
comparison per direction.
"""
import os, json
import torch
import numpy as np
from PIL import Image
from transformers import AutoModel

MODEL_ID = "facebook/dinov2-base"
SC = "/workspace/trent-with-smart-prompts"
SAMPLES_DIR = f"{SC}/notes/probe_samples"

IMAGE_MEAN = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
IMAGE_STD = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)


def preprocess(img):
    img = img.convert("RGB")
    w, h = img.size
    shortest = 256
    if w < h:
        new_w, new_h = shortest, round(h * shortest / w)
    else:
        new_h, new_w = shortest, round(w * shortest / h)
    img = img.resize((new_w, new_h), Image.BICUBIC)
    left = (new_w - 224) // 2
    top = (new_h - 224) // 2
    img = img.crop((left, top, left + 224, top + 224))
    arr = np.asarray(img).astype(np.float32) / 255.0
    t = torch.from_numpy(arr).permute(2, 0, 1)
    t = (t - IMAGE_MEAN) / IMAGE_STD
    return t


def embed_images(paths):
    with torch.no_grad():
        tensors = [preprocess(Image.open(p)) for p in paths]
        pixel_values = torch.stack(tensors, dim=0)
        out = model(pixel_values=pixel_values)
        feats = out.pooler_output
        feats = feats / feats.norm(dim=-1, keepdim=True)
    return feats


print("loading model...", flush=True)
model = AutoModel.from_pretrained(MODEL_ID)
model.eval()

real_dir = f"{SC}/corrected_dataset_extract"
real_paths = sorted([os.path.join(real_dir, f) for f in os.listdir(real_dir) if f.lower().endswith((".jpg", ".jpeg", ".png"))])
real_embs = embed_images(real_paths)
centroid = real_embs.mean(dim=0)
centroid = centroid / centroid.norm()
intra = (real_embs @ centroid).tolist()
print(f"real self-similarity to centroid: mean={sum(intra)/len(intra):.4f} min={min(intra):.4f}\n")

checkpoint_dirs = sorted(
    d for d in os.listdir(SAMPLES_DIR)
    if os.path.isdir(os.path.join(SAMPLES_DIR, d)) and any(
        f.endswith(".png") for f in os.listdir(os.path.join(SAMPLES_DIR, d))
    )
)

results = {}
for name in checkpoint_dirs:
    d = os.path.join(SAMPLES_DIR, name)
    paths = sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith(".png"))
    if not paths:
        continue
    embs = embed_images(paths)
    sims = (embs @ centroid).tolist()
    nn_matrix = embs @ real_embs.T
    nn_sims = nn_matrix.max(dim=1).values.tolist()
    results[name] = {
        "n_images": len(paths),
        "centroid_mean": sum(sims) / len(sims),
        "centroid_per_image": sims,
        "nn_mean": sum(nn_sims) / len(nn_sims),
    }
    print(f"{name:<16} centroid_mean={results[name]['centroid_mean']:.4f}  nn_mean={results[name]['nn_mean']:.4f}  (n={len(paths)})")

with open(f"{SC}/notes/probe_samples/scores.json", "w") as f:
    json.dump(results, f, indent=1)

print("\n--- probe (156) vs full (780) ranking, per direction ---")
directions = sorted(set(n.rsplit("_", 1)[0] for n in results))
probe_scores = {d: results[f"{d}_156"]["centroid_mean"] for d in directions if f"{d}_156" in results}
full_scores = {d: results[f"{d}_780"]["centroid_mean"] for d in directions if f"{d}_780" in results}

probe_rank = sorted(probe_scores, key=lambda d: -probe_scores[d])
full_rank = sorted(full_scores, key=lambda d: -full_scores[d])
print(f"156-step ranking (best to worst): {probe_rank}")
print(f"780-step ranking (best to worst): {full_rank}")
print(f"({len(full_rank)}/{len(probe_rank)} directions have a full-length score so far)")
