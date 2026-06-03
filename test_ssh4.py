import subprocess
import time

# 用 OpenSSH 直接连接，密码通过 stdin 不好传
# 改用: 先生成 ssh key 或者用 expect 风格
# 最简单: 用 ssh 的 -o BatchMode=no 让它等待输入

print("=== Testing SSH with password ===")

# Windows OpenSSH 不支持 sshpass
# 但我们可以用 subprocess + 线程来处理密码输入

import threading

def send_password(proc, password):
    """延迟发送密码"""
    time.sleep(3)  # 等待密码提示
    try:
        proc.stdin.write(password + "\n")
        proc.stdin.flush()
        print(f"Sent password (length={len(password)})")
    except Exception as e:
        print(f"Failed to send password: {e}")

cmd = ["C:\\Windows\\System32\\OpenSSH\\ssh.exe",
       "-o", "StrictHostKeyChecking=accept-new",
       "-o", "ConnectTimeout=10",
       "root@64.90.1.179",
       "uname -a && python3 --version && free -h"]

print(f"Running: {' '.join(cmd)}")

proc = subprocess.Popen(cmd,
                       stdin=subprocess.PIPE,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE,
                       text=True)

# 启动线程发送密码
t = threading.Thread(target=send_password, args=(proc, "sqdSndJ2r2nqaGfu"))
t.daemon = True
t.start()

try:
    stdout, stderr = proc.communicate(timeout=25)
    print(f"\nReturn code: {proc.returncode}")
    if stdout.strip():
        print(f"STDOUT:\n{stdout}")
    if stderr.strip():
        print(f"STDERR:\n{stderr}")
except subprocess.TimeoutExpired:
    proc.kill()
    print("TIMEOUT after 25s")
