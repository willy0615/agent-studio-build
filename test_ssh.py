import subprocess
import sys

# SSH 连接测试
cmd = [
    "ssh",
    "-o", "StrictHostKeyChecking=no",
    "-o", "ConnectTimeout=10",
    "root@64.90.1.179",
    "uname -a && python3 --version 2>&1 || python --version 2>&1"
]

result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("Return code:", result.returncode)
