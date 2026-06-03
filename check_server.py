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

# Check what's in the directory
print("=" * 60)
print("Checking /root/AgentProject structure...")
stdin, stdout, stderr = ssh.exec_command(f"find {REMOTE_DIR} -name 'main.py' -type f 2>/dev/null", timeout=30)
result = stdout.read().decode().strip()
print(f"Found main.py at:\n{result if result else 'NOT FOUND'}")
print("=" * 60)

# List top-level files
print("\nTop-level files:")
stdin, stdout, stderr = ssh.exec_command(f"ls -lh {REMOTE_DIR}/*.py 2>/dev/null | head -20", timeout=10)
result = stdout.read().decode().strip()
print(result if result else "No .py files in root")

# Check app/ directory
print(f"\nContents of {REMOTE_DIR}/app/:")
stdin, stdout, stderr = ssh.exec_command(f"ls -lh {REMOTE_DIR}/app/ 2>/dev/null", timeout=10)
result = stdout.read().decode().strip()
print(result if result else "app/ directory not found or empty")

# Check if Streamlit is installed
print("\nChecking Streamlit installation:")
stdin, stdout, stderr = ssh.exec_command("python3 -m streamlit --version 2>&1 || which streamlit", timeout=10)
result = stdout.read().decode().strip()
print(result if result else "Streamlit not found")

ssh.close()
print("\n[OK] Check complete")
