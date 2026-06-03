"""文件操作工具"""
import os
from pathlib import Path
from typing import Dict, Any, Optional
import shutil


# 工作目录限制（安全沙箱）
WORKSPACE_DIR = Path("E:/AgentProject/workspace")
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)


def _resolve_path(path: str) -> Path:
    """解析路径，限制在工作目录内"""
    p = Path(path)
    if not p.is_absolute():
        p = WORKSPACE_DIR / p
    # 安全检查：防止路径穿越
    try:
        p.resolve().relative_to(WORKSPACE_DIR.resolve())
    except ValueError:
        raise PermissionError(f"Access denied: path outside workspace: {path}")
    return p


def read_file(path: str) -> Dict[str, Any]:
    """读取文件内容"""
    try:
        file_path = _resolve_path(path)
        if not file_path.exists():
            return {"error": f"File not found: {path}"}
        
        # 自动检测编码
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
        content = None
        for enc in encodings:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue
        
        if content is None:
            # 尝试二进制
            with open(file_path, 'rb') as f:
                content = f.read()
            return {"type": "binary", "size": len(content), "path": str(file_path)}
        
        return {
            "type": "text",
            "content": content[:50000],  # 限制返回大小
            "size": len(content),
            "path": str(file_path),
        }
    except Exception as e:
        return {"error": str(e)}


def write_file(path: str, content: str) -> Dict[str, Any]:
    """写入文件"""
    try:
        file_path = _resolve_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        
        return {
            "success": True,
            "path": str(file_path),
            "size": len(content),
        }
    except Exception as e:
        return {"error": str(e)}


def list_directory(path: str = ".") -> Dict[str, Any]:
    """列出目录内容"""
    try:
        dir_path = _resolve_path(path)
        if not dir_path.exists():
            return {"error": f"Directory not found: {path}"}
        
        items = []
        for item in dir_path.iterdir():
            items.append({
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None,
            })
        
        return {
            "path": str(dir_path),
            "items": sorted(items, key=lambda x: (x["type"] == "file", x["name"])),
        }
    except Exception as e:
        return {"error": str(e)}


def delete_file(path: str) -> Dict[str, Any]:
    """删除文件或目录"""
    try:
        file_path = _resolve_path(path)
        if not file_path.exists():
            return {"error": f"Path not found: {path}"}
        
        if file_path.is_dir():
            shutil.rmtree(file_path)
        else:
            file_path.unlink()
        
        return {"success": True, "deleted": str(file_path)}
    except Exception as e:
        return {"error": str(e)}


def create_directory(path: str) -> Dict[str, Any]:
    """创建目录"""
    try:
        dir_path = _resolve_path(path)
        dir_path.mkdir(parents=True, exist_ok=True)
        return {"success": True, "path": str(dir_path)}
    except Exception as e:
        return {"error": str(e)}
