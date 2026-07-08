import os, sys, json
import torch
import numpy as np
from PIL import Image
from transformers import AutoModel

MODEL_ID = "facebook/dinov2-base"
SC = "/workspace/trent-with-smart-prompts"
REAL_DIR = f"{SC}/corrected_dataset_extract"
GEN_DIR = sys.argv[1] if len(sys.argv) > 1 else f"{SC}/art_batch"
N_PERMUTATIONS = 2000

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

real_paths = sorted([os.path.join(REAL_DIR, f) for f in os.listdir(REAL_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))])
gen_paths = sorted([os.path.join(GEN_DIR, f) for f in os.listdir(GEN_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))])
print(f"real images: {len(real_paths)}, generated images: {len(gen_paths)} (from {GEN_DIR})")

real_embs = embed_images(real_paths)
gen_embs = embed_images(gen_paths)

m, n = real_embs.shape[0], gen_embs.shape[0]
all_embs = torch.cat([real_embs, gen_embs], dim=0)  # [m+n, 768], unit vectors

# cosine similarity matrix -> squared Euclidean distance, since ||x-y||^2 = 2 - 2*cos_sim for unit vectors
cos_sim = all_embs @ all_embs.T
sq_dist = (2 - 2 * cos_sim).clamp(min=0)

# median heuristic bandwidth: median of the off-diagonal squared distances
N = m + n
off_diag_mask = ~torch.eye(N, dtype=torch.bool)
median_sq_dist = sq_dist[off_diag_mask].median().item()
sigma2 = median_sq_dist
print(f"\nbandwidth (median heuristic): sigma^2={sigma2:.4f}")

K = torch.exp(-sq_dist / (2 * sigma2))  # full [N, N] RBF kernel matrix, computed once

def mmd2_unbiased(K, idx_a, idx_b):
    a, b = len(idx_a), len(idx_b)
    Kaa = K[idx_a][:, idx_a]
    Kbb = K[idx_b][:, idx_b]
    Kab = K[idx_a][:, idx_b]
    term_aa = (Kaa.sum() - Kaa.diag().sum()) / (a * (a - 1))
    term_bb = (Kbb.sum() - Kbb.diag().sum()) / (b * (b - 1))
    term_ab = Kab.sum() / (a * b)
    mmd2 = term_aa + term_bb - 2 * term_ab
    return mmd2.item(), term_aa.item(), term_bb.item(), term_ab.item()

real_idx = torch.arange(0, m)
gen_idx = torch.arange(m, m + n)
mmd2, real_real, gen_gen, real_gen = mmd2_unbiased(K, real_idx, gen_idx)

print(f"\nkernel terms:")
print(f"  real-real avg similarity (self-cohesion of the 31 real images): {real_real:.4f}")
print(f"  gen-gen avg similarity  (self-cohesion of the {n} generated images): {gen_gen:.4f}")
print(f"  real-gen avg similarity (cross term, how alike the two piles are): {real_gen:.4f}")
print(f"\nMMD^2 = {mmd2:.4f}  (0 = indistinguishable distributions, larger = more different)")

# permutation test: reshuffle the N labels many times, recompute MMD^2 from the same fixed K
rng = np.random.default_rng(0)
perm_scores = np.empty(N_PERMUTATIONS)
all_idx = np.arange(N)
for i in range(N_PERMUTATIONS):
    perm = rng.permutation(all_idx)
    p_real, p_gen = torch.from_numpy(perm[:m]), torch.from_numpy(perm[m:])
    perm_scores[i] = mmd2_unbiased(K, p_real, p_gen)[0]

p_value = (perm_scores >= mmd2).mean()
print(f"\npermutation test ({N_PERMUTATIONS} shuffles): p-value={p_value:.4f}")
print("(low p-value = the real/generated split is a genuinely more different pairing than random splits of the same pool)")

# noise-floor baseline: split the 31 REAL images into two random halves and measure MMD
# between them. There's no true difference between the halves, so this is pure sampling
# noise, the yardstick the real-vs-generated MMD above should be compared against.
N_SELF_SPLITS = 200
self_mmd2 = np.empty(N_SELF_SPLITS)
real_idx_np = real_idx.numpy()
for i in range(N_SELF_SPLITS):
    shuffled = rng.permutation(real_idx_np)
    half = m // 2
    a, b = torch.from_numpy(shuffled[:half]), torch.from_numpy(shuffled[half:])
    self_mmd2[i] = mmd2_unbiased(K, a, b)[0]

print(f"\nreal-vs-real self-split baseline ({N_SELF_SPLITS} random halvings of the 31 real images):")
print(f"  mean={self_mmd2.mean():.4f}  min={self_mmd2.min():.4f}  max={self_mmd2.max():.4f}")
print(f"  observed real-vs-generated MMD^2 ({mmd2:.4f}) is "
      f"{mmd2 / self_mmd2.mean():.1f}x the self-split mean" if self_mmd2.mean() > 0 else "")

with open(f"{SC}/whitepaper/mmd_result.json", "w") as f:
    json.dump({
        "gen_dir": GEN_DIR, "n_real": m, "n_gen": n, "sigma2": sigma2,
        "real_real": real_real, "gen_gen": gen_gen, "real_gen": real_gen,
        "mmd2": mmd2, "p_value": float(p_value), "n_permutations": N_PERMUTATIONS,
        "self_split_mean": float(self_mmd2.mean()), "self_split_min": float(self_mmd2.min()),
        "self_split_max": float(self_mmd2.max()),
    }, f, indent=1)
