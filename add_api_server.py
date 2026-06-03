#!/usr/bin/env python3
"""
Add FastAPI layer to remote server for desktop app to call
"""
import paramiko
import time
import sys

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

# Server info
HOST = "64.90.1.179"
USER = "root"
PASS = "sqdSndJ2r2nqaGfu"

# FastAPI server code (to be written to server)
API_SERVER_CODE = '''#!/usr/bin/env python3
"""
Agent Project API Server - REST API for desktop app
Running on port 8000
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import sys
import os
import time

# Add project path
sys.path.insert(0, "/root/AgentProject")

try:
    from app.agents.autonomous import AutonomousAgent
    from app.config import NVIDIA_API_KEY, NVIDIA_BASE_URL, DEFAULT_MODEL
    agent = AutonomousAgent()
    BACKEND_AVAILABLE = True
except Exception as e:
    print(f"Warning: Cannot import backend: {e}")
    BACKEND_AVAILABLE = False

app = FastAPI(title="Agent Project API", version="1.0.0")

class ChatRequest(BaseModel):
    message: str
    model: str = "deepseek-ai/deepseek-v4-flash"
    mode: str = "auto"
    history: Optional[List[dict]] = None

class ChatResponse(BaseModel):
    success: bool
    answer: str
    mode: str
    time_ms: int
    tool_calls: List[str] = []

@app.get("/")
async def root():
    return {"status": "ok", "message": "Agent Project API Server is running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "backend_available": BACKEND_AVAILABLE}

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat endpoint"""
    if not BACKEND_AVAILABLE:
        raise HTTPException(status_code=503, detail="Backend not available")
    
    try:
        start = time.time()
        
        # Call AutonomousAgent
        result = agent.run(
            task=request.message,
            model=request.model,
            mode=request.mode,
            context=str(request.history) if request.history else ""
        )
        
        elapsed = int((time.time() - start) * 1000)
        
        return ChatResponse(
            success=True,
            answer=result.get("answer", ""),
            mode=result.get("mode", request.mode),
            time_ms=elapsed,
            tool_calls=result.get("tool_calls", [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/models")
async def get_models():
    """Get available models"""
    return {
        "models": [
            "deepseek-ai/deepseek-v4-flash",
            "deepseek-ai/deepseek-v4-pro",
            "z-ai/glm-5.1",
            "nvidia/nemotron-3-120b"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''

def main():
    print("=" * 60)
    print("Add FastAPI layer to remote server")
    print("=" * 60)
    
    # Connect to server
    print(f"\n[1/4] Connecting to {HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(HOST, username=USER, password=PASS, timeout=10)
        print("[OK] Connected")
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return
    
    sftp = ssh.open_sftp()
    
    # Create API server file
    print("\n[2/4] Creating api_server.py...")
    remote_path = "/root/AgentProject/api_server.py"
    
    with sftp.open(remote_path, "w") as f:
        f.write(API_SERVER_CODE)
    
    print(f"[OK] Created {remote_path}")
    
    # Install FastAPI and uvicorn
    print("\n[3/4] Installing FastAPI and uvicorn...")
    stdin, stdout, stderr = ssh.exec_command("cd /root/AgentProject && pip3 install fastapi uvicorn -q")
    exit_code = stdout.channel.recv_exit_status()
    
    if exit_code == 0:
        print("[OK] FastAPI and uvicorn installed")
    else:
        print("[WARN] Installation may have failed, but continuing...")
    
    # Start API server (background)
    print("\n[4/4] Starting API server (port 8000)...")
    command = "cd /root/AgentProject && nohup python3 api_server.py > api_server.log 2>&1 &"
    stdin, stdout, stderr = ssh.exec_command(command)
    time.sleep(3)
    
    # Check if started successfully
    stdin, stdout, stderr = ssh.exec_command("curl -s http://localhost:8000/health")
    response = stdout.read().decode()
    
    if "healthy" in response:
        print("[OK] API server started successfully!")
        print(f"[OK] Endpoint: http://{HOST}:8000")
        print(f"[OK] Chat endpoint: http://{HOST}:8000/api/chat")
    else:
        print("[WARN] API server may not have started, check logs")
        stdin, stdout, stderr = ssh.exec_command("cd /root/AgentProject && tail -20 api_server.log")
        print(stdout.read().decode())
    
    sftp.close()
    ssh.close()
    
    print("\n" + "=" * 60)
    print("Done! Now modify desktop app to call this API")
    print("=" * 60)

if __name__ == "__main__":
    main()
