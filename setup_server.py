import paramiko
import time

# Config
REMOTE_HOST = "64.90.1.179"
REMOTE_USER = "root"
REMOTE_PASS = "sqdSndJ2r2nqaGfu"
REMOTE_DIR = "/root/AgentProject"

print("Connecting to server...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(REMOTE_HOST, username=REMOTE_USER, password=REMOTE_PASS, timeout=15, allow_agent=False, look_for_keys=False)

print("[OK] Connected\n")

# Commands to run
commands = [
    ("Check files", f"ls -lh {REMOTE_DIR}"),
    ("Check Python", "python3 --version || python --version"),
    ("Check pip", "pip3 --version || pip --version"),
    ("Install deps", f"cd {REMOTE_DIR} && pip3 install -r requirements.txt -q"),
    ("Check .env", f"cat {REMOTE_DIR}/.env | head -5"),
    ("Start backend", f"cd {REMOTE_DIR} && python3 app/main.py &"),
]

for desc, cmd in commands:
    print(f"\n{'='*60}")
    print(f"[{desc}]")
    print(f"$ {cmd}")
    print('='*60)
    
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True, timeout=300)
    
    # For long-running commands, just show first 50 lines
    lines = 0
    for line in stdout:
        print(line.rstrip())
        lines += 1
        if lines > 50:
            print("... (output truncated)")
            break
    
    err = stderr.read().decode().strip()
    if err:
        print(f"STDERR: {err}")

ssh.close()
print("\n\n[OK] All done!")
