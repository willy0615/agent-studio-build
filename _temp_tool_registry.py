"""全能Agent工具集 - 扩展工具库"""
from app.tools.web_search import search_web, fetch_url
from app.tools.code_executor import execute_code
from app.tools.calculator import calculate
from app.tools.file_ops import read_file, write_file, list_directory, delete_file
from app.tools.api_caller import call_api
from app.tools.data_processor import process_data
from app.tools.document_parser import parse_file
from typing import Dict, Any, List, Optional
import json


class ToolRegistry:
    """工具注册中心 - 统一管理所有工具"""
    
    _tools: Dict[str, Dict] = {}
    
    @classmethod
    def register(cls, name: str, func: callable, description: str, parameters: dict):
        """注册工具"""
        cls._tools[name] = {
            "name": name,
            "function": func,
            "description": description,
            "parameters": parameters,
        }
    
    @classmethod
    def get_tool(cls, name: str) -> Optional[Dict]:
        """获取工具"""
        return cls._tools.get(name)
    
    @classmethod
    def list_tools(cls) -> List[Dict]:
        """列出所有工具"""
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"],
            }
            for t in cls._tools.values()
        ]
    
    @classmethod
    def execute(cls, name: str, **kwargs) -> Dict[str, Any]:
        """执行工具"""
        tool = cls.get_tool(name)
        if not tool:
            return {"error": f"Tool '{name}' not found"}
        
        try:
            result = tool["function"](**kwargs)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}


# 注册核心工具
ToolRegistry.register(
    "web_search",
    search_web,
    "搜索互联网获取最新信息",
    {
        "query": {"type": "string", "description": "搜索关键词"},
        "num_results": {"type": "integer", "description": "返回结果数量", "default": 5},
    }
)

ToolRegistry.register(
    "fetch_url",
    fetch_url,
    "抓取网页内容",
    {
        "url": {"type": "string", "description": "网页URL"},
    }
)

ToolRegistry.register(
    "execute_code",
    execute_code,
    "执行Python代码",
    {
        "code": {"type": "string", "description": "Python代码"},
    }
)

ToolRegistry.register(
    "calculate",
    calculate,
    "执行数学计算",
    {
        "expression": {"type": "string", "description": "数学表达式"},
    }
)

ToolRegistry.register(
    "read_file",
    read_file,
    "读取本地文件",
    {
        "path": {"type": "string", "description": "文件路径"},
    }
)

ToolRegistry.register(
    "write_file",
    write_file,
    "写入本地文件",
    {
        "path": {"type": "string", "description": "文件路径"},
        "content": {"type": "string", "description": "文件内容"},
    }
)

ToolRegistry.register(
    "list_directory",
    list_directory,
    "列出目录内容",
    {
        "path": {"type": "string", "description": "目录路径"},
    }
)

ToolRegistry.register(
    "call_api",
    call_api,
    "调用外部API",
    {
        "url": {"type": "string", "description": "API URL"},
        "method": {"type": "string", "description": "HTTP方法", "enum": ["GET", "POST", "PUT", "DELETE"]},
        "headers": {"type": "object", "description": "请求头"},
        "body": {"type": "object", "description": "请求体"},
    }
)

ToolRegistry.register(
    "process_data",
    process_data,
    "处理数据（CSV、JSON等）",
    {
        "data": {"type": "string", "description": "数据内容"},
        "operation": {"type": "string", "description": "操作类型", "enum": ["parse", "filter", "transform", "aggregate"]},
        "params": {"type": "object", "description": "操作参数"},
    }
)
