import paramiko

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

# Commands
commands = [
    ("Check pip module", "python3 -m pip --version"),
    ("Install pip", "python3 -m ensurepip --upgrade || curl -sS https://bootstrap.pypa.io/get-pip.py | python3"),
    ("Verify pip", "python3 -m pip --version"),
    ("Install deps", f"cd {REMOTE_DIR} && python3 -m pip install -r requirements.txt -q --no-warn-script-location"),
    ("Check deps", f"cd {REMOTE_DIR} && python3 -c 'import streamlit; import langchain; import chromadb; print(\"Deps OK\")'"),
    ("Start backend (test)", f"cd {REMOTE_DIR} && python3 -c 'from app.config import *; print(\"Config OK\")'"),
]

for desc, cmd in commands:
    print(f"\n{'='*60}")
    print(f"[{desc}]")
    print(f"$ {cmd}")
    print('='*60)
    
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True, timeout=300)
    
    # Read output
    lines = 0
    for line in stdout:
        print(line.rstrip())
        lines += 1
        if lines > 100:
            print("... (output truncated)")
            break
    
    err = stderr.read().decode().strip()
    if err and lines < 100:
        print(f"STDERR: {err}")

ssh.close()
print("\n\n[OK] All done!")
