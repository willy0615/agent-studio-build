"""
Agent Project FastAPI Backend
调用 NVIDIA NIM API (OpenAI compatible)
端口: 8000
"""
import os
import time
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import urllib.request
import urllib.error

app = FastAPI(title="Agent Project API", version="1.0.0")

# 配置
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "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")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "deepseek-ai/deepseek-v4-flash")


class ChatRequest(BaseModel):
    message: str
    model: str = DEFAULT_MODEL
    mode: str = "auto"
    history: Optional[List[Dict[str, Any]]] = None


class ChatResponse(BaseModel):
    success: bool
    answer: str
    mode: str
    time_ms: int
    tool_calls: List[str] = []


@app.get("/")
def root():
    return {"status": "ok", "service": "agent-project-api"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/api/models")
def get_models():
    return {
        "models": [
            "deepseek-ai/deepseek-v4-flash",
            "deepseek-ai/deepseek-v4-pro",
            "z-ai/glm-5.1",
            "nvidia/nemotron-3-120b",
        ]
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    start_time = time.time()
    
    try:
        # 构建消息
        messages = []
        if req.history:
            for msg in req.history:
                if msg.get("role") in ["user", "assistant"]:
                    messages.append({
                        "role": msg["role"],
                        "content": msg.get("content", "")
                    })
        
        # 添加系统提示
        messages.insert(0, {
            "role": "system",
            "content": "你是一个有用的AI助手。请用中文回答问题。"
        })
        
        # 添加用户消息
        messages.append({"role": "user", "content": req.message})
        
        # 调用 NVIDIA API (OpenAI compatible)
        url = NVIDIA_BASE_URL + "/chat/completions"
        payload = json.dumps({
            "model": req.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000,
            "stream": False
        }).encode("utf-8")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + NVIDIA_API_KEY,
            "Accept": "application/json"
        }
        
        req_http = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        
        with urllib.request.urlopen(req_http, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        
        answer = result["choices"][0]["message"]["content"]
        elapsed = int((time.time() - start_time) * 1000)
        
        return ChatResponse(
            success=True,
            answer=answer,
            mode=req.mode,
            time_ms=elapsed,
            tool_calls=[]
        )
        
    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode("utf-8")
        except Exception:
            pass
        print(f"NVIDIA API Error {e.code}: {error_body}")
        raise HTTPException(status_code=500, detail=f"NVIDIA API error: {e.code} - {error_body}")
    except Exception as e:
        print(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
