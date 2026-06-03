import socket
import time

print("Testing port 22 on 64.90.1.179...")
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(10)
result = sock.connect_ex(("64.90.1.179", 22))
if result == 0:
    print("Port 22 is OPEN")
else:
    print(f"Port 22 is CLOSED (error: {result})")
sock.close()

# Also test common ports
for port in [80, 443, 2222, 8080]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    result = sock.connect_ex(("64.90.1.179", port))
    status = "OPEN" if result == 0 else "closed"
    print(f"Port {port}: {status}")
    sock.close()
