import sys, paramiko

HOST = "213.173.98.39"
PORT = 16775
KEY = "/workspace/trent-with-smart-prompts/runpod-ssh/id_ed25519"

local_path, remote_path = sys.argv[1], sys.argv[2]

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pkey = paramiko.Ed25519Key.from_private_key_file(KEY)
client.connect(HOST, port=PORT, username="root", pkey=pkey, timeout=20)
sftp = client.open_sftp()
sftp.put(local_path, remote_path)
sftp.close()
client.close()
print("uploaded", local_path, "->", remote_path)
