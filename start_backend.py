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

# Step 1: Kill existing streamlit processes
print("=" * 60)
print("[Step 1] Killing existing Streamlit processes...")
stdin, stdout, stderr = ssh.exec_command("pkill -f streamlit || true", timeout=10)
print("[OK] Done")
print("=" * 60)

# Step 2: Start backend with nohup
print("\n[Step 2] Starting backend server...")
cmd = f"cd {REMOTE_DIR} && nohup streamlit run app/main.py --server.port 8501 --server.address 0.0.0.0 > /tmp/streamlit.log 2>&1 &"
stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
print(f"[OK] Backend starting on port 8501")

# Step 3: Wait and check
print("\n[Step 3] Waiting for backend to start (10s)...")
time.sleep(10)

# Step 4: Check if process is running
print("\n[Step 4] Checking if backend is running...")
stdin, stdout, stderr = ssh.exec_command("ps aux | grep streamlit | grep -v grep", timeout=10)
result = stdout.read().decode().strip()
if result:
    print("[OK] Backend is running:")
    print(result)
else:
    print("[ERROR] Backend NOT running")
    # Check log
    stdin, stdout, stderr = ssh.exec_command("tail -20 /tmp/streamlit.log", timeout=10)
    log = stdout.read().decode().strip()
    print(f"Log:\n{log}")

# Step 5: Check port
print("\n[Step 5] Checking port 8501...")
stdin, stdout, stderr = ssh.exec_command("netstat -tlnp | grep 8501 || ss -tlnp | grep 8501", timeout=10)
result = stdout.read().decode().strip()
if result:
    print(f"[OK] Port 8501 is open:\n{result}")
else:
    print("[WARN] Port 8501 not found in netstat")
    print("Checking if streamlit is still running...")
    stdin, stdout, stderr = ssh.exec_command("ps aux | grep streamlit", timeout=10)
    print(stdout.read().decode().strip())

# Step 6: Test HTTP endpoint
print("\n[Step 6] Testing HTTP endpoint...")
stdin, stdout, stderr = ssh.exec_command("curl -s -o /dev/null -w '%{http_code}' http://localhost:8501", timeout=10)
result = stdout.read().decode().strip()
if result == "200":
    print("[OK] Backend HTTP endpoint is accessible (200)")
else:
    print(f"[WARN] HTTP status: {result}")

ssh.close()

print("\n" + "=" * 60)
print("BACKEND DEPLOYED SUCCESSFULLY!")
print("=" * 60)
print(f"Backend URL: http://{REMOTE_HOST}:8501")
print(f"API Base URL: http://{REMOTE_HOST}:8501")
print("\nNext steps:")
print("1. Update desktop app to connect to this backend")
print("2. Or access web UI directly at the URL above")
print("=" * 60)
