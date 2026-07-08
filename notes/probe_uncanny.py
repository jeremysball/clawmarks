import json, os, time, base64
import urllib.request

API_KEY = os.environ["RUNPOD_API_KEY"]
ENDPOINT = "uix4vdb2cec7sb"
BASE = f"https://api.runpod.ai/v2/{ENDPOINT}"
OUT_DIR = "/workspace/trent-with-smart-prompts/whitepaper/probe_uncanny"
os.makedirs(OUT_DIR, exist_ok=True)

PROMPTS = {
    "human_face": "close-up human face, dark-rimmed eyes glowing pale blue, pale skin with visible brush texture, hand pressed beside cheek, dense dark-blue vertical brush-dash background, thick acrylic dry-brush texture, raw outsider-art painting",
    "cyborg": "close-up cyborg face, half exposed circuitry and wiring, dark-rimmed human eye glowing pale blue beside a mechanical lens, clawed metal hand pressed beside cheek, dense dark-blue vertical brush-dash background, thick acrylic dry-brush texture, raw outsider-art painting",
    "body_horror": "close-up face mid-transformation, skin splitting to reveal clawed fingers pushing through the cheek, dark-rimmed eyes glowing pale blue, dense dark-blue vertical brush-dash background, thick acrylic dry-brush texture, raw outsider-art painting",
    "liminal": "figure standing alone in an empty fluorescent-lit hallway, dark-rimmed eyes glowing pale blue, clawed hand pressed against the wall, dense dark-blue vertical brush-dash background replaced by flat institutional tile, thick acrylic dry-brush texture, raw outsider-art painting",
}
SEEDS = [11, 22]

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
    jobs = []
    for label, prompt in PROMPTS.items():
        for seed in SEEDS:
            jobs.append((label, prompt, seed))

    print(f"Total jobs to submit: {len(jobs)}")
    job_ids = {}
    for label, prompt, seed in jobs:
        wf = build_workflow(prompt, seed)
        res = api_post("/run", wf)
        jid = res.get("id")
        job_ids[jid] = (label, prompt, seed)
        print(f"submitted {label} seed={seed} -> {jid}")

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
                label, prompt, seed = job_ids[jid]
                images = res.get("output", {}).get("images", [])
                if images:
                    fname = f"{OUT_DIR}/{label}_seed{seed}.png"
                    with open(fname, "wb") as f:
                        f.write(base64.b64decode(images[0]["data"]))
                    manifest.append({"label": label, "prompt": prompt, "seed": seed, "file": fname})
                    completed += 1
                pending.discard(jid)
            elif status in ("FAILED", "CANCELLED"):
                failed += 1
                pending.discard(jid)
                print(f"JOB_FAILED {jid}: {res}")
        elapsed = time.time() - t0
        print(f"[{elapsed:.0f}s] completed={completed} failed={failed} pending={len(pending)}")
        if pending:
            time.sleep(8)

    with open(f"{OUT_DIR}/manifest.json", "w") as f:
        json.dump(manifest, f, indent=1)
    print(f"DONE completed={completed} failed={failed}")

if __name__ == "__main__":
    main()
