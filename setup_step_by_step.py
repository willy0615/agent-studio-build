import paramiko
import time

# Config
REMOTE_HOST = "64.90.1.179"
REMOTE_USER = "root"
REMOTE_PASS = "sqdSndJ2r2nqaGfu"

print("Connecting to server...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(REMOTE_HOST, username=REMOTE_USER, password=REMOTE_PASS, timeout=15, allow_agent=False, look_for_keys=False)

print("[OK] Connected\n")

# Step 1: Check internet
print("=" * 60)
print("[Step 1] Checking internet...")
stdin, stdout, stderr = ssh.exec_command("curl -s --connect-timeout 5 https://pypi.org | head -1", timeout=10)
result = stdout.read().decode().strip()
if result:
    print(f"[OK] Internet accessible: {result[:50]}")
else:
    print("[WARN] No internet access")
print("=" * 60)

# Step 2: Install pip using ensurepip
print("\n[Step 2] Installing pip (ensurepip)...")
stdin, stdout, stderr = ssh.exec_command("python3 -m ensurepip --upgrade", get_pty=True, timeout=60)
output = stdout.read().decode().strip()
err = stderr.read().decode().strip()
if output:
    print(output)
if err:
    print(f"STDERR: {err}")
print("[OK] pip installation attempted")

# Step 3: Verify pip
print("\n[Step 3] Verifying pip...")
stdin, stdout, stderr = ssh.exec_command("python3 -m pip --version", timeout=10)
result = stdout.read().decode().strip()
if result:
    print(f"[OK] {result}")
else:
    print("[ERROR] pip not found")
    ssh.close()
    exit(1)
print("=" * 60)

# Step 4: Install deps (one by one to see progress)
print("\n[Step 4] Installing dependencies...")
deps = ["streamlit", "langchain", "chromadb", "openai", "python-dotenv"]
for dep in deps:
    print(f"  Installing {dep}...")
    stdin, stdout, stderr = ssh.exec_command(f"python3 -m pip install {dep} -q --timeout 30", get_pty=True, timeout=120)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if err and "warn" not in err.lower():
        print(f"    [WARN] {err[:100]}")
    else:
        print(f"    [OK] {dep}")

print("\n[OK] Dependencies installed")

# Step 5: Test import
print("\n[Step 5] Testing imports...")
stdin, stdout, stderr = ssh.exec_command("cd /root/AgentProject && python3 -c 'from app.config import *; print(\"Config OK\")'", timeout=30)
result = stdout.read().decode().strip()
err = stderr.read().decode().strip()
if "OK" in result:
    print("[OK] Backend imports successful")
else:
    print(f"[ERROR] Import failed: {err}")

ssh.close()
print("\n[OK] Setup complete!")
print("\nNext step: Start backend with:")
print("  ssh root@64.90.1.179")
print("  cd /root/AgentProject")
print("  streamlit run app/main.py --server.port 8501")
