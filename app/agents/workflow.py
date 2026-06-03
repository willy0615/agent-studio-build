"""工具链编排 - 自动化复杂工作流"""
from typing import Dict, Any, List, Callable
from app.tools.tool_registry import ToolRegistry
import logging

logger = logging.getLogger(__name__)


class ToolChain:
    """工具链定义"""
    
    def __init__(self, name: str, steps: List[Dict[str, Any]]):
        """
        Args:
            name: 工具链名称
            steps: 步骤列表 [{tool, params_mapping, condition}]
        """
        self.name = name
        self.steps = steps
    
    def execute(self, initial_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具链"""
        result = initial_inputs.copy()
        results_history = []
        
        for i, step in enumerate(self.steps):
            tool_name = step["tool"]
            params_mapping = step.get("params_mapping", {})
            condition = step.get("condition")
            
            # 检查条件
            if condition and not self._check_condition(condition, result):
                logger.info(f"Step {i} ({tool_name}) skipped due to condition")
                continue
            
            # 映射参数
            params = {}
            for param_name, source in params_mapping.items():
                if source == "__input__":
                    params[param_name] = initial_inputs.get(param_name)
                elif source == "__previous__":
                    params[param_name] = result
                elif isinstance(source, str) and source.startswith("$"):
                    # 引用前一步骤的结果
                    key = source[1:]
                    params[param_name] = result.get(key)
                else:
                    params[param_name] = source
            
            # 执行工具
            logger.info(f"Executing step {i}: {tool_name}")
            tool_result = ToolRegistry.execute(tool_name, **params)
            
            # 更新结果
            result.update(tool_result.get("result", {}))
            results_history.append({
                "step": i,
                "tool": tool_name,
                "result": tool_result,
            })
        
        return {
            "success": True,
            "final_result": result,
            "history": results_history,
        }
    
    def _check_condition(self, condition: str, context: Dict) -> bool:
        """检查条件"""
        try:
            return eval(condition, {}, context)
        except:
            return False


# 预定义工具链
PREDEFINED_CHAINS = {
    "research_report": ToolChain(
        name="research_report",
        steps=[
            {
                "tool": "web_search",
                "params_mapping": {
                    "query": "__input__",
                    "num_results": 5,
                },
            },
            {
                "tool": "browse_website",
                "params_mapping": {
                    "url": "$url",
                    "action": "extract",
                },
                "condition": "'url' in result",
            },
            {
                "tool": "parse_document",
                "params_mapping": {
                    "file_path": "$downloaded_file",
                },
                "condition": "'downloaded_file' in result",
            },
        ],
    ),
    
    "data_pipeline": ToolChain(
        name="data_pipeline",
        steps=[
            {
                "tool": "process_excel",
                "params_mapping": {
                    "file_path": "__input__",
                    "operation": "read",
                },
            },
            {
                "tool": "analyze_data",
                "params_mapping": {
                    "file_path": "__input__",
                    "analysis_type": "summary",
                },
            },
            {
                "tool": "create_chart",
                "params_mapping": {
                    "data": "$chart_data",
                    "chart_type": "bar",
                    "title": "数据分析图表",
                },
                "condition": "'chart_data' in result",
            },
        ],
    ),
    
    "document_analysis": ToolChain(
        name="document_analysis",
        steps=[
            {
                "tool": "parse_document",
                "params_mapping": {
                    "file_path": "__input__",
                },
            },
            {
                "tool": "execute_code",
                "params_mapping": {
                    "code": "$analysis_code",
                },
                "condition": "'analysis_code' in result",
            },
        ],
    ),
    
    "web_scraping": ToolChain(
        name="web_scraping",
        steps=[
            {
                "tool": "browse_website",
                "params_mapping": {
                    "url": "__input__",
                    "action": "screenshot",
                },
            },
            {
                "tool": "analyze_image",
                "params_mapping": {
                    "image_path": "$screenshot",
                    "question": "描述这个网页的内容和结构",
                },
            },
        ],
    ),
    
    "image_to_report": ToolChain(
        name="image_to_report",
        steps=[
            {
                "tool": "analyze_image",
                "params_mapping": {
                    "image_path": "__input__",
                    "question": "详细分析这张图片",
                },
            },
            {
                "tool": "extract_text_from_image",
                "params_mapping": {
                    "image_path": "__input__",
                },
            },
        ],
    ),
}


class ChainOrchestrator:
    """工具链编排器"""
    
    def __init__(self):
        self.chains = PREDEFINED_CHAINS.copy()
    
    def register_chain(self, chain: ToolChain):
        """注册自定义工具链"""
        self.chains[chain.name] = chain
        logger.info(f"Registered chain: {chain.name}")
    
    def execute_chain(self, chain_name: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具链"""
        chain = self.chains.get(chain_name)
        
        if not chain:
            return {
                "success": False,
                "error": f"Chain '{chain_name}' not found",
            }
        
        logger.info(f"Executing chain: {chain_name}")
        return chain.execute(inputs)
    
    def list_chains(self) -> List[Dict[str, Any]]:
        """列出所有工具链"""
        return [
            {
                "name": name,
                "steps": len(chain.steps),
                "step_tools": [s["tool"] for s in chain.steps],
            }
            for name, chain in self.chains.items()
        ]
    
    def create_custom_chain(self, name: str, steps: List[Dict]) -> ToolChain:
        """创建自定义工具链"""
        chain = ToolChain(name=name, steps=steps)
        self.register_chain(chain)
        return chain


# 全局编排器实例
_orchestrator = None


def get_orchestrator() -> ChainOrchestrator:
    """获取全局编排器实例"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ChainOrchestrator()
    return _orchestrator
