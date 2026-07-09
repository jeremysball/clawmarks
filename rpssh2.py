import sys, paramiko

HOST = "47.47.180.44"
PORT = 17882
KEY = "/workspace/trent-with-smart-prompts/runpod-ssh/id_ed25519"

def run(cmd, timeout=None):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    pkey = paramiko.Ed25519Key.from_private_key_file(KEY)
    client.connect(HOST, port=PORT, username="root", pkey=pkey, timeout=20)
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    code = stdout.channel.recv_exit_status()
    client.close()
    print(out)
    if err:
        print("STDERR:", err, file=sys.stderr)
    print(f"EXIT:{code}")
    return code

if __name__ == "__main__":
    cmd = sys.argv[1]
    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else None
    sys.exit(run(cmd, timeout))
