import os, json
import torch
import numpy as np
from PIL import Image
from transformers import AutoModel

MODEL_ID = "facebook/dinov2-base"
SC = "/workspace/trent-with-smart-prompts"
PROBE_DIR = f"{SC}/notes/probe_uncanny"

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
print(f"real self-similarity: mean={sum(intra)/len(intra):.4f} min={min(intra):.4f} max={max(intra):.4f}")

probe_paths = sorted([os.path.join(PROBE_DIR, f) for f in os.listdir(PROBE_DIR) if f.endswith(".png")])
probe_embs = embed_images(probe_paths)
sims = (probe_embs @ centroid).tolist()

results = sorted(zip(probe_paths, sims), key=lambda x: -x[1])
print("\nProbe scores vs real centroid:")
for p, s in results:
    print(f"  {s:.4f}  {os.path.basename(p)}")
