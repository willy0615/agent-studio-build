"""全能Agent工具集 - 统一工具注册"""
from app.tools.web_search import search_web, fetch_url
from app.tools.code_executor import execute_code
from app.tools.calculator import calculate
from app.tools.file_ops import read_file, write_file, list_directory, delete_file
from app.tools.api_caller import call_api
from app.tools.data_processor import process_data
from app.tools.document_parser import parse_file
from app.tools.image_analyzer import analyze_image, extract_text_from_image
from app.tools.data_analyzer import analyze_data, create_chart, process_excel
from app.tools.speech import transcribe_audio, text_to_speech
from app.tools.web_automation import browse_website, download_file
from app.tools.notifications import send_email, send_webhook, send_desktop_notification
from typing import Dict, Any, List, Optional


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


# ========== 核心工具（9个） ==========

ToolRegistry.register(
    "web_search", search_web, "搜索互联网获取最新信息",
    {"query": {"type": "string", "description": "搜索关键词"}, "num_results": {"type": "integer", "description": "返回结果数量", "default": 5}},
)

ToolRegistry.register(
    "fetch_url", fetch_url, "抓取网页内容",
    {"url": {"type": "string", "description": "网页URL"}},
)

ToolRegistry.register(
    "execute_code", execute_code, "在沙箱中执行Python代码",
    {"code": {"type": "string", "description": "Python代码"}},
)

ToolRegistry.register(
    "calculate", calculate, "执行数学计算",
    {"expression": {"type": "string", "description": "数学表达式"}},
)

ToolRegistry.register(
    "read_file", read_file, "读取本地文件",
    {"path": {"type": "string", "description": "文件路径"}},
)

ToolRegistry.register(
    "write_file", write_file, "写入本地文件",
    {"path": {"type": "string", "description": "文件路径"}, "content": {"type": "string", "description": "文件内容"}},
)

ToolRegistry.register(
    "list_directory", list_directory, "列出目录内容",
    {"path": {"type": "string", "description": "目录路径"}},
)

ToolRegistry.register(
    "call_api", call_api, "调用外部API",
    {"url": {"type": "string", "description": "API URL"}, "method": {"type": "string", "description": "HTTP方法", "enum": ["GET", "POST", "PUT", "DELETE"]}, "headers": {"type": "object", "description": "请求头"}, "body": {"type": "object", "description": "请求体"}},
)

ToolRegistry.register(
    "process_data", process_data, "处理数据（CSV、JSON等）",
    {"data": {"type": "string", "description": "数据内容"}, "operation": {"type": "string", "description": "操作类型", "enum": ["parse", "filter", "transform", "aggregate"]}, "params": {"type": "object", "description": "操作参数"}},
)

# ========== 增强工具 ==========

# 文档解析
ToolRegistry.register(
    "parse_document", parse_file, "解析文档（PDF、Word、Excel、HTML等）",
    {"file_path": {"type": "string", "description": "文件路径"}, "file_type": {"type": "string", "description": "文件类型（可选，自动检测）"}},
)

# 图像分析
ToolRegistry.register(
    "analyze_image", analyze_image, "分析图像内容（多模态理解）",
    {"image_path": {"type": "string", "description": "图像路径"}, "question": {"type": "string", "description": "关于图像的问题", "default": "描述这张图片"}},
)

ToolRegistry.register(
    "ocr_image", extract_text_from_image, "从图像中提取文字（OCR）",
    {"image_path": {"type": "string", "description": "图像路径"}},
)

# 数据分析
ToolRegistry.register(
    "analyze_data", analyze_data, "分析数据文件（CSV、Excel）",
    {"file_path": {"type": "string", "description": "数据文件路径"}, "analysis_type": {"type": "string", "description": "分析类型", "enum": ["summary", "stats", "query"]}, "query": {"type": "string", "description": "自然语言查询（可选）"}},
)

ToolRegistry.register(
    "create_chart", create_chart, "创建图表（柱状图、折线图、饼图等）",
    {"data": {"type": "object", "description": "图表数据 {labels: [...], values: [...]}"}, "chart_type": {"type": "string", "description": "图表类型", "enum": ["bar", "line", "pie", "scatter"]}, "title": {"type": "string", "description": "图表标题"}},
)

ToolRegistry.register(
    "process_excel", process_excel, "处理Excel文件",
    {"file_path": {"type": "string", "description": "Excel文件路径"}, "operation": {"type": "string", "description": "操作类型", "enum": ["read", "filter", "aggregate", "pivot"]}, "params": {"type": "object", "description": "操作参数"}},
)

# 语音
ToolRegistry.register(
    "transcribe_audio", transcribe_audio, "语音转文字",
    {"audio_path": {"type": "string", "description": "音频文件路径"}, "language": {"type": "string", "description": "语言（zh/en/auto）", "default": "auto"}},
)

ToolRegistry.register(
    "text_to_speech", text_to_speech, "文字转语音",
    {"text": {"type": "string", "description": "要转换的文字"}, "language": {"type": "string", "description": "语言（zh/en）", "default": "zh"}},
)

# 网页自动化
ToolRegistry.register(
    "browse_website", browse_website, "浏览器自动化（访问、点击、提取、截图）",
    {"url": {"type": "string", "description": "网站URL"}, "action": {"type": "string", "description": "操作类型", "enum": ["visit", "click", "type", "extract", "screenshot"]}, "selector": {"type": "string", "description": "CSS选择器（可选）"}},
)

ToolRegistry.register(
    "download_file", download_file, "下载文件",
    {"url": {"type": "string", "description": "文件URL"}, "output_path": {"type": "string", "description": "保存路径（可选）"}},
)

# 通知
ToolRegistry.register(
    "send_email", send_email, "发送邮件",
    {"to": {"type": "string", "description": "收件人邮箱"}, "subject": {"type": "string", "description": "邮件主题"}, "body": {"type": "string", "description": "邮件内容"}},
)

ToolRegistry.register(
    "send_webhook", send_webhook, "发送Webhook通知",
    {"url": {"type": "string", "description": "Webhook URL"}, "data": {"type": "object", "description": "发送的数据"}},
)

ToolRegistry.register(
    "send_notification", send_desktop_notification, "发送桌面通知",
    {"title": {"type": "string", "description": "通知标题"}, "message": {"type": "string", "description": "通知内容"}},
)
