import json, os, time, base64, sys
import urllib.request

import os
API_KEY = os.environ["RUNPOD_API_KEY"]
ENDPOINT = "uix4vdb2cec7sb"
BASE = f"https://api.runpod.ai/v2/{ENDPOINT}"
OUT_DIR = "/workspace/trent-with-smart-prompts/art_batch"
os.makedirs(OUT_DIR, exist_ok=True)

SEEDS = [1001, 2002, 3003, 4004, 5005]

def build_workflow(prompt, seed):
    return {
        "input": {
            "workflow": {
                "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "illustrious_v0.1.safetensors"}},
                "2": {"class_type": "LoraLoader", "inputs": {
                    "lora_name": "clawmarks-illustrious-v3-epoch4.safetensors",
                    "strength_model": 1.0, "strength_clip": 1.0,
                    "model": ["1", 0], "clip": ["1", 1]}},
                "3": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 1]}},
                "4": {"class_type": "CLIPTextEncode", "inputs": {"text": "low quality, blurry, watermark", "clip": ["2", 1]}},
                "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
                "6": {"class_type": "KSampler", "inputs": {
                    "seed": seed, "steps": 28, "cfg": 7.5, "sampler_name": "ddim", "scheduler": "normal",
                    "denoise": 1.0, "model": ["2", 0], "positive": ["3", 0], "negative": ["4", 0],
                    "latent_image": ["5", 0]}},
                "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
                "8": {"class_type": "SaveImage", "inputs": {"images": ["7", 0], "filename_prefix": "clawmarks"}}
            }
        }
    }

def api_post(path, payload):
    req = urllib.request.Request(f"{BASE}{path}", data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def api_get(path):
    req = urllib.request.Request(f"{BASE}{path}", headers={"Authorization": f"Bearer {API_KEY}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def main():
    with open("/tmp/art_prompts_base_v2.txt") as f:
        base_prompts = [l.strip() for l in f if l.strip()]

    jobs = []
    idx = 0
    for p in base_prompts:
        for s in SEEDS:
            idx += 1
            jobs.append((idx, p, s))

    print(f"Total jobs to submit: {len(jobs)}")

    job_ids = {}
    for idx, prompt, seed in jobs:
        wf = build_workflow(prompt, seed)
        try:
            res = api_post("/run", wf)
            jid = res.get("id")
            job_ids[jid] = (idx, prompt, seed)
        except Exception as e:
            print(f"SUBMIT_FAIL idx={idx}: {e}")
        if idx % 25 == 0:
            print(f"submitted {idx}/{len(jobs)}")

    with open(f"{OUT_DIR}/job_map.json", "w") as f:
        json.dump({jid: v for jid, v in job_ids.items()}, f)

    print(f"All {len(job_ids)} jobs submitted. Polling for completion...")

    pending = set(job_ids.keys())
    completed = 0
    failed = 0
    manifest = []
    t0 = time.time()
    while pending:
        for jid in list(pending):
            try:
                res = api_get(f"/status/{jid}")
            except Exception:
                continue
            status = res.get("status")
            if status == "COMPLETED":
                idx, prompt, seed = job_ids[jid]
                images = res.get("output", {}).get("images", [])
                if images:
                    fname = f"{OUT_DIR}/img_{idx:03d}.png"
                    with open(fname, "wb") as f:
                        f.write(base64.b64decode(images[0]["data"]))
                    manifest.append({"idx": idx, "prompt": prompt, "seed": seed, "file": fname})
                    completed += 1
                pending.discard(jid)
            elif status in ("FAILED", "CANCELLED"):
                failed += 1
                pending.discard(jid)
                print(f"JOB_FAILED {jid}: {res}")
        elapsed = time.time() - t0
        print(f"[{elapsed:.0f}s] completed={completed} failed={failed} pending={len(pending)}")
        if pending:
            time.sleep(10)

    with open(f"{OUT_DIR}/manifest.json", "w") as f:
        json.dump(manifest, f, indent=1)
    print(f"DONE completed={completed} failed={failed}")

if __name__ == "__main__":
    main()
