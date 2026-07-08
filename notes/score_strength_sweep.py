import os, json
import torch
import numpy as np
from PIL import Image
from transformers import AutoModel

MODEL_ID = "facebook/dinov2-base"
SC = "/workspace/trent-with-smart-prompts"
SWEEP_DIR = f"{SC}/notes/probe_strength"

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

print("loading model...", flush=True)
model = AutoModel.from_pretrained(MODEL_ID)
model.eval()

def embed_images(paths):
    with torch.no_grad():
        tensors = [preprocess(Image.open(p)) for p in paths]
        pixel_values = torch.stack(tensors, dim=0)
        out = model(pixel_values=pixel_values)
        feats = out.pooler_output
        feats = feats / feats.norm(dim=-1, keepdim=True)
    return feats

real_dir = f"{SC}/corrected_dataset_extract"
real_paths = sorted([os.path.join(real_dir, f) for f in os.listdir(real_dir) if f.lower().endswith((".jpg",".jpeg",".png"))])
real_embs = embed_images(real_paths)
centroid = real_embs.mean(dim=0)
centroid = centroid / centroid.norm()
intra = (real_embs @ centroid).tolist()
print(f"real self-similarity to centroid: mean={sum(intra)/len(intra):.4f} min={min(intra):.4f} max={max(intra):.4f}")

with open(f"{SWEEP_DIR}/manifest.json") as f:
    manifest = json.load(f)

paths = [m["file"] for m in manifest]
embs = embed_images(paths)
centroid_sims = (embs @ centroid).tolist()
# nearest-neighbor: max similarity to any single real image
nn_matrix = embs @ real_embs.T  # [n_gen, n_real]
nn_sims = nn_matrix.max(dim=1).values.tolist()

results = []
for m, csim, nnsim in zip(manifest, centroid_sims, nn_sims):
    results.append({**m, "centroid_score": csim, "nn_score": nnsim})

results.sort(key=lambda r: -r["centroid_score"])
with open(f"{SWEEP_DIR}/scores.json", "w") as f:
    json.dump(results, f, indent=1)

print(f"\n{'label':<28} {'strength':>8} {'centroid':>10} {'nn_max':>8}")
for r in results:
    print(f"{r['label']:<28} {r['strength']:>8} {r['centroid_score']:>10.4f} {r['nn_score']:>8.4f}")
