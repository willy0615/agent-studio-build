"""API调用工具"""
import requests
from typing import Dict, Any, Optional
import json


def call_api(
    url: str,
    method: str = "GET",
    headers: Optional[Dict] = None,
    body: Optional[Dict] = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    """调用外部API
    
    Args:
        url: API URL
        method: HTTP方法 (GET/POST/PUT/DELETE)
        headers: 请求头
        body: 请求体 (JSON)
        timeout: 超时时间(秒)
    
    Returns:
        响应结果
    """
    try:
        method = method.upper()
        if method not in ["GET", "POST", "PUT", "DELETE"]:
            return {"error": f"Invalid HTTP method: {method}"}
        
        kwargs = {
            "url": url,
            "headers": headers or {},
            "timeout": timeout,
        }
        
        if method in ["POST", "PUT"] and body:
            kwargs["json"] = body
        
        response = requests.request(method, **kwargs)
        
        # 尝试解析JSON
        try:
            data = response.json()
        except:
            data = response.text[:5000]  # 限制文本长度
        
        return {
            "success": response.status_code < 400,
            "status_code": response.status_code,
            "data": data,
            "headers": dict(response.headers),
        }
    
    except requests.Timeout:
        return {"error": f"Request timeout after {timeout}s"}
    except requests.ConnectionError as e:
        return {"error": f"Connection error: {e}"}
    except Exception as e:
        return {"error": str(e)}
