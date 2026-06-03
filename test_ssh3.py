# 测试 SSH 连接 - 用 subprocess + pipe 传密码
import subprocess

# 方法: 用 sshpass 的 Windows 替代方案
# 直接用 ssh 并设置 StrictHostKeyChecking
cmd = r'''echo y | "C:\Windows\System32\OpenSSH\ssh.exe" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 root@64.90.1.179 "uname -a; python3 --version; free -h"'''

print("Running SSH command...")
proc = subprocess.Popen(cmd, shell=True, 
                       stdin=subprocess.PIPE,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE,
                       text=True)

try:
    stdout, stderr = proc.communicate(timeout=30)
    print(f"Return code: {proc.returncode}")
    print(f"STDOUT:\n{stdout}")
    if stderr:
        print(f"STDERR:\n{stderr}")
except subprocess.TimeoutExpired:
    proc.kill()
    stdout, stderr = proc.communicate()
    print("TIMEOUT")
    print(f"Partial STDOUT: {stdout}")
    print(f"Partial STDERR: {stderr}")
