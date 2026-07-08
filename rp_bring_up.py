"""
Bring up a fresh RunPod training pod and leave it ready for kohya_ss LoRA training.

Single entry point: creates the pod via the RunPod API, waits for SSH, points
rpssh.py/rpget.py/rpsftp.py at it, uploads the dataset + setup script, and runs
setup remotely (installs uv-pinned torch/xformers, clones kohya_ss, downloads the
base checkpoint). Re-running against an already-set-up pod is fast: each setup
step checks for its own completion marker and skips if already done.
"""
import json, os, re, sys, time
import urllib.request
import paramiko

API_KEY = os.environ["RUNPOD_API_KEY"]
CIVITAI_TOKEN = os.environ["CIVITAI_TOKEN"]
GRAPHQL = f"https://api.runpod.io/graphql?api_key={API_KEY}"
SC = "/workspace/trent-with-smart-prompts"
KEY_PATH = f"{SC}/runpod-ssh/id_ed25519"
PUBLIC_KEY = open(f"{SC}/runpod-ssh/id_ed25519.pub").read().strip()

GPU_PRIORITY = ["NVIDIA GeForce RTX 4090", "NVIDIA GeForce RTX 3090", "NVIDIA RTX A5000"]
IMAGE = "runpod/pytorch:2.4.1-py3.11-cuda12.4.1-devel-ubuntu22.04"
POD_NAME = "clawmarks-training"


def gql(query):
    req = urllib.request.Request(
        GRAPHQL, data=json.dumps({"query": query}).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.loads(r.read())
    if "errors" in res:
        raise RuntimeError(res["errors"])
    return res["data"]


def stock_status(gpu_id):
    data = gql(f'query {{ gpuTypes(input: {{id: "{gpu_id}"}}) {{ lowestPrice(input: {{gpuCount: 1}}) {{ stockStatus uninterruptablePrice }} }} }}')
    lp = data["gpuTypes"][0]["lowestPrice"]
    return lp["stockStatus"], lp["uninterruptablePrice"]


def pick_gpu():
    for gpu in GPU_PRIORITY:
        status, price = stock_status(gpu)
        print(f"  {gpu}: stock={status} price={price}")
        if status in ("High", "Medium"):
            return gpu
    raise RuntimeError("no GPU in the priority list has usable stock right now")


def create_pod(gpu_id):
    mutation = f'''
    mutation {{
      podFindAndDeployOnDemand(input: {{
        cloudType: SECURE
        gpuCount: 1
        volumeInGb: 60
        containerDiskInGb: 60
        minVcpuCount: 4
        minMemoryInGb: 15
        gpuTypeId: "{gpu_id}"
        name: "{POD_NAME}"
        imageName: "{IMAGE}"
        ports: "22/tcp"
        volumeMountPath: "/workspace"
        env: [{{ key: "PUBLIC_KEY", value: "{PUBLIC_KEY}" }}]
      }}) {{
        id
      }}
    }}'''
    data = gql(mutation)
    return data["podFindAndDeployOnDemand"]["id"]


def wait_for_ssh(pod_id, timeout=600):
    print(f"waiting for pod {pod_id} to boot and expose SSH...")
    t0 = time.time()
    while time.time() - t0 < timeout:
        data = gql(f'''query {{
          pod(input: {{podId: "{pod_id}"}}) {{
            id desiredStatus
            runtime {{ ports {{ ip isIpPublic privatePort publicPort type }} }}
          }}
        }}''')
        pod = data["pod"]
        runtime = pod.get("runtime")
        if runtime and runtime.get("ports"):
            for p in runtime["ports"]:
                if p["privatePort"] == 22 and p["isIpPublic"]:
                    print(f"  SSH ready: {p['ip']}:{p['publicPort']}")
                    return p["ip"], p["publicPort"]
        elapsed = int(time.time() - t0)
        print(f"  [{elapsed}s] status={pod['desiredStatus']} runtime={'up' if runtime else 'not yet'}")
        time.sleep(10)
    raise TimeoutError("pod never exposed a public SSH port in time")


def update_helper_scripts(host, port):
    for fname in ("rpssh.py", "rpget.py", "rpsftp.py"):
        path = f"{SC}/{fname}"
        text = open(path).read()
        text = re.sub(r'HOST = ".*"', f'HOST = "{host}"', text)
        text = re.sub(r'PORT = \d+', f'PORT = {port}', text)
        open(path, "w").write(text)
    print(f"updated rpssh.py / rpget.py / rpsftp.py -> {host}:{port}")


def ssh_client(host, port):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    pkey = paramiko.Ed25519Key.from_private_key_file(KEY_PATH)
    for attempt in range(10):
        try:
            client.connect(host, port=port, username="root", pkey=pkey, timeout=20)
            return client
        except Exception as e:
            print(f"  ssh connect attempt {attempt+1} failed ({e}), retrying...")
            time.sleep(10)
    raise RuntimeError("could not establish SSH after pod reported ready")


def run_cmd(client, cmd, timeout=1800):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    for line in iter(stdout.readline, ""):
        print(line, end="")
    code = stdout.channel.recv_exit_status()
    err = stderr.read().decode(errors="replace")
    if err.strip():
        print("STDERR:", err, file=sys.stderr)
    return code


def upload_dataset_and_setup(client, host, port):
    sftp = client.open_sftp()
    sftp.put(f"{SC}/notes/remote_setup.sh", "/workspace/remote_setup.sh")

    local_zip = f"{SC}/clawmarks-dataset.zip"
    if not os.path.exists(local_zip):
        import zipfile
        real_dir = f"{SC}/corrected_dataset_extract"
        with zipfile.ZipFile(local_zip, "w") as z:
            for f in os.listdir(real_dir):
                z.write(os.path.join(real_dir, f), f)
        print(f"zipped dataset -> {local_zip}")
    sftp.put(local_zip, "/workspace/clawmarks-dataset.zip")
    sftp.close()
    print("uploaded dataset + setup script")

    run_cmd(client, f"chmod +x /workspace/remote_setup.sh && CIVITAI_TOKEN={CIVITAI_TOKEN} /workspace/remote_setup.sh")


def main():
    print("checking GPU availability...")
    gpu_id = pick_gpu()
    print(f"deploying on {gpu_id}")
    pod_id = create_pod(gpu_id)
    print(f"pod created: {pod_id}")
    host, port = wait_for_ssh(pod_id)
    update_helper_scripts(host, port)
    client = ssh_client(host, port)
    upload_dataset_and_setup(client, host, port)
    client.close()
    print(f"\nDONE. Pod {pod_id} at {host}:{port} ready for training.")
    print(f"rpssh.py / rpget.py / rpsftp.py now point at this pod.")


if __name__ == "__main__":
    main()
