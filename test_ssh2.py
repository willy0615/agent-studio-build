import subprocess
import sys

# 用 echo 传密码给 ssh (不安全但有效)
# 或者用 paramiko
try:
    import paramiko
    print("paramiko available")
except ImportError:
    print("no paramiko, installing...")
    subprocess.run([sys.executable, "-m", "pip", "install", "paramiko", "-q"], check=True)
    import paramiko

# 连接服务器
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

print("Connecting to 64.90.1.179...")
ssh.connect("64.90.1.179", username="root", password="sqdSndJ2r2nqaGfu", timeout=15)

# 执行命令
commands = [
    "uname -a",
    "python3 --version || python --version",
    "pip3 --version || pip --version",
    "free -h",
    "df -h /",
]

for cmd in commands:
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    print(f"\n$ {cmd}")
    if out:
        print(out)
    if err:
        print(f"ERR: {err}")

ssh.close()
print("\nDone!")
