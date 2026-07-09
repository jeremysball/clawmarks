"""
Generate the fixed 4-prompt sample set from a trained checkpoint, directly on the pod, via
kohya's sdxl_gen_img.py. Used for every probe/full checkpoint so different directions and
lengths are visually and quantitatively comparable on identical prompts/seed/sampler settings.

Usage:
  python3 notes/gen_samples.py --checkpoint controlB_156 --pod 1
  python3 notes/gen_samples.py --checkpoint controlB_156 --pod 1 --remote-ckpt-dir controlB_156

Looks for /workspace/output/<checkpoint>/<checkpoint>.safetensors on the pod (the final-epoch
checkpoint kohya also saves under the run's own name), generates 4 images (seed 42, 28-step
DDIM, scale 7.5, 1024x1024) from the fixed prompt set, and downloads them into
notes/probe_samples/<checkpoint>/im_00000{1..4}.png.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, "/workspace/trent-with-smart-prompts")
import paramiko

SC = "/workspace/trent-with-smart-prompts"
KEY_PATH = f"{SC}/runpod-ssh/id_ed25519"
LOCAL_PROMPTS_FILE = "/tmp/art_prompts_base_v2.txt"
PROMPT_LINES = [1, 41, 47, 50]  # cat split-color, galloping horse, tiger stripe fragment, wolf-cat hybrid
SEED = 42
STEPS = 28
SCALE = 7.5
RESOLUTION = "1024,1024"


def read_host_port(host_module):
    text = open(host_module).read()
    host = re.search(r'HOST = "(.*)"', text).group(1)
    port = int(re.search(r"PORT = (\d+)", text).group(1))
    return host, port


def ssh_client(pod):
    host_module = f"{SC}/rpssh.py" if pod == 1 else f"{SC}/rpssh{pod}.py"
    host, port = read_host_port(host_module)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    pkey = paramiko.Ed25519Key.from_private_key_file(KEY_PATH)
    client.connect(host, port=port, username="root", pkey=pkey, timeout=20)
    client.get_transport().set_keepalive(30)
    return client


def run_cmd(client, cmd, timeout=None):
    print(f"+ {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    for line in iter(stdout.readline, ""):
        print(line, end="")
    code = stdout.channel.recv_exit_status()
    err = stderr.read().decode(errors="replace")
    if err.strip():
        print("STDERR:", err, file=sys.stderr)
    return code


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True, help="run name, e.g. controlB_156")
    ap.add_argument("--pod", type=int, default=1, choices=[1, 2])
    ap.add_argument("--remote-ckpt-dir", default=None, help="defaults to --checkpoint")
    args = ap.parse_args()

    remote_dir = args.remote_ckpt_dir or args.checkpoint
    remote_ckpt = f"/workspace/output/{remote_dir}/{args.checkpoint}.safetensors"
    remote_out = f"/workspace/samples_out/{args.checkpoint}"
    remote_prompts = f"/workspace/prompts_{args.checkpoint}.txt"

    with open(LOCAL_PROMPTS_FILE) as f:
        all_lines = f.read().splitlines()
    prompts = [all_lines[i - 1] for i in PROMPT_LINES]

    client = ssh_client(args.pod)
    sftp = client.open_sftp()
    with sftp.open(remote_prompts, "w") as rf:
        rf.write("\n".join(prompts) + "\n")
    sftp.close()

    run_cmd(client, f"mkdir -p {remote_out}")
    cmd = " ".join([
        "source /workspace/venv/bin/activate &&",
        "cd /workspace/kohya_ss &&",
        "python3 sdxl_gen_img.py",
        "--ckpt /workspace/models/illustrious_v0.1.safetensors",
        f"--network_module networks.lora --network_weights {remote_ckpt}",
        f"--from_file {remote_prompts}",
        f"--outdir {remote_out}",
        f"--seed {SEED}",
        f"--steps {STEPS}",
        f"--scale {SCALE}",
        f"--W {RESOLUTION.split(',')[0]} --H {RESOLUTION.split(',')[1]}",
        "--sampler ddim",
        "--images_per_prompt 1",
        "--xformers",
        f"> {remote_out}/gen.log 2>&1",
    ])
    code = run_cmd(client, cmd, timeout=1200)
    if code != 0:
        print(f"GENERATION FAILED (exit {code}), see remote log at {remote_out}/gen.log")
        client.close()
        sys.exit(code)

    local_dir = f"{SC}/notes/probe_samples/{args.checkpoint}"
    os.makedirs(local_dir, exist_ok=True)
    sftp = client.open_sftp()
    remote_files = sorted(f for f in sftp.listdir(remote_out) if f.endswith(".png"))
    for i, fname in enumerate(remote_files, start=1):
        local_name = f"im_{i:06d}.png"
        sftp.get(f"{remote_out}/{fname}", f"{local_dir}/{local_name}")
        print(f"downloaded {fname} -> {local_name}")
    sftp.close()
    client.close()
    print(f"DONE: {args.checkpoint} -> {local_dir}")


if __name__ == "__main__":
    main()
