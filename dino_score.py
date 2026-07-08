import os, json
import torch
import numpy as np
from PIL import Image
from transformers import AutoModel

MODEL_ID = "facebook/dinov2-base"
SC = "/workspace/trent-with-smart-prompts"

IMAGE_MEAN = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
IMAGE_STD = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)

def preprocess(img: Image.Image) -> torch.Tensor:
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

def embed_images(paths, batch_size=16):
    embs = []
    with torch.no_grad():
        for i in range(0, len(paths), batch_size):
            batch_paths = paths[i:i+batch_size]
            tensors = [preprocess(Image.open(p)) for p in batch_paths]
            pixel_values = torch.stack(tensors, dim=0)
            out = model(pixel_values=pixel_values)
            feats = out.pooler_output
            feats = feats / feats.norm(dim=-1, keepdim=True)
            embs.append(feats)
            print(f"  embedded {i+len(batch_paths)}/{len(paths)}", flush=True)
    return torch.cat(embs, dim=0)

real_dir = f"{SC}/corrected_dataset_extract"
real_paths = sorted([os.path.join(real_dir, f) for f in os.listdir(real_dir) if f.lower().endswith((".jpg",".jpeg",".png"))])
print(f"real training images: {len(real_paths)}")

gen_dir = f"{SC}/art_batch"
gen_paths = sorted([os.path.join(gen_dir, f) for f in os.listdir(gen_dir) if f.endswith(".png")])
print(f"generated images: {len(gen_paths)}")

real_embs = embed_images(real_paths)
centroid = real_embs.mean(dim=0)
centroid = centroid / centroid.norm()

gen_embs = embed_images(gen_paths)
sims = (gen_embs @ centroid).tolist()

results = []
for p, s in zip(gen_paths, sims):
    results.append({"file": p, "score": s})
results.sort(key=lambda r: -r["score"])

with open(f"{SC}/dino_scores.json", "w") as f:
    json.dump({"model": MODEL_ID, "real_images": len(real_paths), "results": results}, f, indent=1)

intra = (real_embs @ centroid).tolist()
print(f"real-image self-similarity to centroid: mean={sum(intra)/len(intra):.4f} min={min(intra):.4f} max={max(intra):.4f}")
print(f"generated-image similarity to centroid: mean={sum(sims)/len(sims):.4f} min={min(sims):.4f} max={max(sims):.4f}")
print("Top 15:")
for r in results[:15]:
    print(f"  {r['score']:.4f}  {os.path.basename(r['file'])}")
print("Bottom 15:")
for r in results[-15:]:
    print(f"  {r['score']:.4f}  {os.path.basename(r['file'])}")
