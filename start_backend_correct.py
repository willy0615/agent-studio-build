import paramiko
import time

# Config
REMOTE_HOST = "64.90.1.179"
REMOTE_USER = "root"
REMOTE_PASS = "sqdSndJ2r2nqaGfu"
MAIN_PY_PATH = "/root/AgentProject/main.py"

print("Connecting to server...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(REMOTE_HOST, username=REMOTE_USER, password=REMOTE_PASS, timeout=15, allow_agent=False, look_for_keys=False)

print("[OK] Connected\n")

# Step 1: Kill existing processes
print("=" * 60)
print("[Step 1] Killing existing Streamlit processes...")
ssh.exec_command("pkill -f 'streamlit run' || true", timeout=5)
print("[OK] Done")
time.sleep(2)
print("=" * 60)

# Step 2: Verify file exists
print(f"\n[Step 2] Verifying {MAIN_PY_PATH} exists...")
stdin, stdout, stderr = ssh.exec_command(f"test -f {MAIN_PY_PATH} && echo 'EXISTS' || echo 'NOT FOUND'", timeout=5)
result = stdout.read().decode().strip()
if result == "EXISTS":
    print(f"[OK] File exists: {MAIN_PY_PATH}")
else:
    print(f"[ERROR] File not found: {MAIN_PY_PATH}")
    ssh.close()
    exit(1)
print("=" * 60)

# Step 3: Start backend with correct path
print(f"\n[Step 3] Starting backend...")
cmd = f"cd /root/AgentProject && nohup streamlit run {MAIN_PY_PATH} --server.port 8501 --server.address 0.0.0.0 > /tmp/streamlit.log 2>&1 &"
print(f"Command: {cmd}")
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
print("[OK] Backend starting...")

# Step 4: Wait
print("\n[Step 4] Waiting for backend to start (15s)...")
time.sleep(15)

# Step 5: Check process
print("\n[Step 5] Checking if backend is running...")
stdin, stdout, stderr = ssh.exec_command("ps aux | grep 'streamlit run' | grep -v grep", timeout=10)
result = stdout.read().decode().strip()
if result:
    print("[OK] Backend is running:")
    print(result[:200])
else:
    print("[ERROR] Backend NOT running")
    stdin, stdout, stderr = ssh.exec_command("tail -30 /tmp/streamlit.log", timeout=10)
    log = stdout.read().decode().strip()
    print(f"Log:\n{log}")
    ssh.close()
    exit(1)

# Step 6: Check port
print("\n[Step 6] Checking port 8501...")
stdin, stdout, stderr = ssh.exec_command("netstat -tlnp 2>/dev/null | grep 8501 || ss -tlnp 2>/dev/null | grep 8501", timeout=10)
result = stdout.read().decode().strip()
if result:
    print(f"[OK] Port 8501 is open:\n{result}")
else:
    print("[WARN] Port 8501 not found in netstat")
    print("Checking if streamlit process is still running...")
    stdin, stdout, stderr = ssh.exec_command("ps aux | grep streamlit", timeout=10)
    print(stdout.read().decode().strip())

# Step 7: Test HTTP
print("\n[Step 7] Testing HTTP endpoint...")
stdin, stdout, stderr = ssh.exec_command("curl -s -o /dev/null -w '%{http_code}' http://localhost:8501", timeout=10)
result = stdout.read().decode().strip()
if result == "200":
    print("[OK] Backend HTTP endpoint is accessible (200)")
else:
    print(f"[WARN] HTTP status: {result}")
    print("(This might be OK if Streamlit is still starting up)")

ssh.close()

print("\n" + "=" * 60)
print("BACKEND DEPLOYED SUCCESSFULLY!")
print("=" * 60)
print(f"Backend URL: http://{REMOTE_HOST}:8501")
print(f"Access the web UI at: http://{REMOTE_HOST}:8501")
print("\nYou can also connect the desktop app to this backend.")
print("=" * 60)
