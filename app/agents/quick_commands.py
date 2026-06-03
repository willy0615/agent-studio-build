"""快捷命令系统 - 自然语言触发复杂操作"""
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class QuickCommand:
    """快捷命令定义"""
    name: str
    description: str
    patterns: List[str]  # 正则表达式模式列表
    action: Callable
    examples: List[str]
    category: str = "general"


class QuickCommandRegistry:
    """快捷命令注册中心"""
    
    def __init__(self):
        self.commands: List[QuickCommand] = []
        self._register_default_commands()
    
    def register(self, command: QuickCommand):
        """注册命令"""
        self.commands.append(command)
        logger.info(f"Registered quick command: {command.name}")
    
    def match(self, text: str) -> Optional[QuickCommand]:
        """匹配文本到命令"""
        text_lower = text.lower().strip()
        
        for command in self.commands:
            for pattern in command.patterns:
                try:
                    if re.search(pattern, text_lower, re.IGNORECASE):
                        return command
                except re.error:
                    # 如果模式无效，尝试简单匹配
                    if pattern.lower() in text_lower:
                        return command
        
        return None
    
    def execute(self, text: str, **kwargs) -> Dict[str, Any]:
        """执行匹配的命令"""
        command = self.match(text)
        
        if not command:
            return {
                "success": False,
                "error": "No matching command found",
            }
        
        try:
            logger.info(f"Executing quick command: {command.name}")
            result = command.action(text, **kwargs)
            
            return {
                "success": True,
                "command": command.name,
                "result": result,
            }
        except Exception as e:
            logger.error(f"Failed to execute command {command.name}: {e}")
            return {
                "success": False,
                "command": command.name,
                "error": str(e),
            }
    
    def list_commands(self) -> List[Dict[str, Any]]:
        """列出所有命令"""
        return [
            {
                "name": cmd.name,
                "description": cmd.description,
                "examples": cmd.examples,
                "category": cmd.category,
            }
            for cmd in self.commands
        ]
    
    def _register_default_commands(self):
        """注册默认命令"""
        
        # === 数据分析类 ===
        
        def analyze_data_action(text: str, **kwargs):
            from app.tools.tool_registry import ToolRegistry
            
            # 提取文件路径
            import re
            file_match = re.search(r'["\']?([^\s"\']+\.(xlsx?|csv))["\']?', text)
            file_path = file_match.group(1) if file_match else kwargs.get("file_path")
            
            if not file_path:
                return {"error": "请提供数据文件路径"}
            
            return ToolRegistry.execute("analyze_data", file_path=file_path, analysis_type="summary")
        
        self.register(QuickCommand(
            name="analyze_data",
            description="快速分析数据文件",
            patterns=[
                r"分析.*数据",
                r"分析.*xlsx",
                r"分析.*csv",
                r"数据.*分析",
            ],
            action=analyze_data_action,
            examples=["分析 sales.xlsx", "分析这个CSV数据"],
            category="data",
        ))
        
        # === 图像分析类 ===
        
        def analyze_image_action(text: str, **kwargs):
            from app.tools.tool_registry import ToolRegistry
            
            # 提取问题
            question = text
            
            return ToolRegistry.execute(
                "analyze_image",
                image_path=kwargs.get("image_path"),
                question=question,
            )
        
        self.register(QuickCommand(
            name="analyze_image",
            description="快速分析图像",
            patterns=[
                r"分析.*图片",
                r"识别.*图像",
                r"看.*图片",
                r"这张.*是什么",
            ],
            action=analyze_image_action,
            examples=["分析这张图片", "识别图像内容"],
            category="vision",
        ))
        
        # === 网页抓取类 ===
        
        def scrape_web_action(text: str, **kwargs):
            from app.tools.tool_registry import ToolRegistry
            
            # 提取URL
            import re
            url_match = re.search(r'https?://[^\s]+', text)
            url = url_match.group(0) if url_match else kwargs.get("url")
            
            if not url:
                return {"error": "请提供网页URL"}
            
            return ToolRegistry.execute("browse_website", url=url, action="extract")
        
        self.register(QuickCommand(
            name="scrape_web",
            description="快速抓取网页",
            patterns=[
                r"抓取.*网页",
                r"爬取.*网站",
                r"提取.*http",
                r"获取.*url",
            ],
            action=scrape_web_action,
            examples=["抓取 https://example.com", "爬取这个网页"],
            category="web",
        ))
        
        # === 代码执行类 ===
        
        def execute_code_action(text: str, **kwargs):
            from app.tools.tool_registry import ToolRegistry
            
            # 提取代码块
            import re
            code_match = re.search(r'```(?:\w+)?\n(.*?)\n```', text, re.DOTALL)
            
            if code_match:
                code = code_match.group(1)
            else:
                code = kwargs.get("code", text)
            
            return ToolRegistry.execute("execute_code", code=code)
        
        self.register(QuickCommand(
            name="execute_code",
            description="快速执行代码",
            patterns=[
                r"运行.*代码",
                r"执行.*代码",
                r"跑一下.*python",
            ],
            action=execute_code_action,
            examples=["运行这段代码", "执行Python代码"],
            category="code",
        ))
        
        # === 搜索类 ===
        
        def search_web_action(text: str, **kwargs):
            from app.tools.tool_registry import ToolRegistry
            
            # 提取搜索词
            import re
            query = re.sub(r'搜索|查找|查询', '', text).strip()
            
            return ToolRegistry.execute("web_search", query=query, num_results=5)
        
        self.register(QuickCommand(
            name="search_web",
            description="快速网页搜索",
            patterns=[
                r"搜索\s*[\w\u4e00-\u9fff]+",
                r"查找\s*[\w\u4e00-\u9fff]+",
                r"查询\s*[\w\u4e00-\u9fff]+",
            ],
            action=search_web_action,
            examples=["搜索 Python教程", "查找最新新闻"],
            category="search",
        ))
        
        # === 文档解析类 ===
        
        def parse_document_action(text: str, **kwargs):
            from app.tools.tool_registry import ToolRegistry
            
            # 提取文件路径
            import re
            file_match = re.search(r'["\']?([^\s"\']+\.(pdf|docx?|txt|md))["\']?', text)
            file_path = file_match.group(1) if file_match else kwargs.get("file_path")
            
            if not file_path:
                return {"error": "请提供文档路径"}
            
            return ToolRegistry.execute("parse_document", file_path=file_path)
        
        self.register(QuickCommand(
            name="parse_document",
            description="快速解析文档",
            patterns=[
                r"解析.*文档",
                r"读取.*pdf",
                r"提取.*pdf",
                r"分析.*文档",
            ],
            action=parse_document_action,
            examples=["解析 report.pdf", "读取这个文档"],
            category="document",
        ))
        
        # === 提醒类 ===
        
        def create_reminder_action(text: str, **kwargs):
            from app.agents.scheduler import get_scheduler
            
            # 提取时间
            import re
            time_match = re.search(r'(\d+)\s*(分钟|小时|天)', text)
            
            if time_match:
                amount = int(time_match.group(1))
                unit = time_match.group(2)
                
                if unit == "分钟":
                    delay_min = amount
                elif unit == "小时":
                    delay_min = amount * 60
                else:  # 天
                    delay_min = amount * 60 * 24
            else:
                delay_min = 60  # 默认1小时
            
            # 提取提醒内容
            message = re.sub(r'提醒|在|后|分钟|小时|天|\d+', '', text).strip()
            
            scheduler = get_scheduler()
            return scheduler.schedule_reminder(message=message, delay_minutes=delay_min)
        
        self.register(QuickCommand(
            name="create_reminder",
            description="快速创建提醒",
            patterns=[
                r"提醒我",
                r"设置提醒",
                r"(\d+)\s*(分钟|小时|天).*提醒",
            ],
            action=create_reminder_action,
            examples=["提醒我开会", "30分钟后提醒我"],
            category="productivity",
        ))
        
        # === 工具链类 ===
        
        def run_chain_action(text: str, **kwargs):
            from app.agents.workflow import get_orchestrator
            
            # 识别工具链
            chains = {
                "研究": "research_report",
                "数据": "data_pipeline",
                "文档": "document_analysis",
                "网页": "web_scraping",
                "图像": "image_to_report",
            }
            
            chain_name = None
            for keyword, name in chains.items():
                if keyword in text:
                    chain_name = name
                    break
            
            if not chain_name:
                return {"error": "无法识别工具链类型"}
            
            orchestrator = get_orchestrator()
            return orchestrator.execute_chain(chain_name, kwargs.get("inputs", {}))
        
        self.register(QuickCommand(
            name="run_chain",
            description="快速执行工具链",
            patterns=[
                r"运行.*工具链",
                r"执行.*链",
                r"自动化.*流程",
            ],
            action=run_chain_action,
            examples=["运行数据分析链", "执行研究工具链"],
            category="workflow",
        ))


# 全局实例
_registry = None


def get_quick_command_registry() -> QuickCommandRegistry:
    """获取全局命令注册中心"""
    global _registry
    if _registry is None:
        _registry = QuickCommandRegistry()
    return _registry


def execute_quick_command(text: str, **kwargs) -> Dict[str, Any]:
    """执行快捷命令（便捷函数）"""
    return get_quick_command_registry().execute(text, **kwargs)
