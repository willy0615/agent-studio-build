import os
import sys

# Config
REMOTE_HOST = "64.90.1.179"
REMOTE_USER = "root"
REMOTE_PASS = "sqdSndJ2r2nqaGfu"
REMOTE_PORT = 22
LOCAL_DIR = r"E:\AgentProject"
REMOTE_DIR = "/root/AgentProject"

print("=" * 60)
print("AgentProject Upload Tool")
print("=" * 60)
print(f"Target: {REMOTE_USER}@{REMOTE_HOST}:{REMOTE_PORT}")
print(f"Local: {LOCAL_DIR}")
print(f"Remote: {REMOTE_DIR}")
print("=" * 60)

# Check paramiko
try:
    import paramiko
    print("[OK] paramiko installed")
except ImportError:
    print("[INFO] Installing paramiko...")
    import subprocess
    ret = subprocess.call([sys.executable, "-m", "pip", "install", "paramiko", "--no-deps", "-q"])
    if ret != 0:
        print("[ERROR] Failed to install paramiko")
        sys.exit(1)
    import paramiko
    print("[OK] paramiko installed")

# Collect files
print("\n[1/4] Scanning files...")
file_list = []
for root, dirs, files in os.walk(LOCAL_DIR):
    dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', '.venv', 'venv', 'node_modules', 'dist', 'build']]
    for file in files:
        if file.endswith(('.pyc', '.exe', '.whl', '.pyd')):
            continue
        local_path = os.path.join(root, file)
        rel_path = os.path.relpath(local_path, LOCAL_DIR)
        file_list.append((local_path, rel_path))

print(f"Found {len(file_list)} files")

# Connect SSH
print("\n[2/4] Connecting to server...")
try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(REMOTE_HOST, port=REMOTE_PORT, username=REMOTE_USER, password=REMOTE_PASS, timeout=15, allow_agent=False, look_for_keys=False)
    print("[OK] SSH connected")
except Exception as e:
    print(f"[ERROR] SSH connection failed: {e}")
    sys.exit(1)

# Create SFTP
print("\n[3/4] Opening SFTP...")
try:
    sftp = ssh.open_sftp()
    print("[OK] SFTP opened")
except Exception as e:
    print(f"[ERROR] SFTP failed: {e}")
    ssh.close()
    sys.exit(1)

# Upload
print(f"\n[4/4] Uploading to {REMOTE_DIR}...")
try:
    try:
        sftp.mkdir(REMOTE_DIR)
        print(f"[OK] Created {REMOTE_DIR}")
    except:
        print(f"[INFO] {REMOTE_DIR} already exists")
    
    uploaded = 0
    failed = 0
    for i, (local_path, rel_path) in enumerate(file_list):
        remote_path = REMOTE_DIR + "/" + rel_path.replace("\\", "/")
        remote_dir = "/".join(remote_path.split("/")[:-1])
        
        try:
            sftp.mkdir(remote_dir)
        except:
            pass
        
        try:
            sftp.put(local_path, remote_path)
            uploaded += 1
            if uploaded % 10 == 0:
                print(f"  Progress: {uploaded}/{len(file_list)}")
        except Exception as e:
            print(f"  [ERROR] {rel_path}: {e}")
            failed += 1
    
    print(f"\n[OK] Upload complete!")
    print(f"  Success: {uploaded} files")
    print(f"  Failed: {failed} files")
    
except Exception as e:
    print(f"[ERROR] Upload failed: {e}")
finally:
    sftp.close()
    ssh.close()
    print("[INFO] Connection closed")

print("\n" + "=" * 60)
print("DONE! Run on server:")
print(f"  ssh root@{REMOTE_HOST}")
print(f"  cd {REMOTE_DIR}")
print(f"  pip3 install -r requirements.txt")
print(f"  python3 app/main.py")
print("=" * 60)
