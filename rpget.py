import sys, paramiko

HOST = "103.196.86.102"
PORT = 11314
KEY = "/workspace/trent-with-smart-prompts/runpod-ssh/id_ed25519"

remote_path, local_path = sys.argv[1], sys.argv[2]

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pkey = paramiko.Ed25519Key.from_private_key_file(KEY)
client.connect(HOST, port=PORT, username="root", pkey=pkey, timeout=20)
sftp = client.open_sftp()
sftp.get(remote_path, local_path)
sftp.close()
client.close()
print("downloaded", remote_path, "->", local_path)
