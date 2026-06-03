"""智能模型路由 - 根据任务自动选择最优模型"""
from typing import Dict, Any, List, Optional, Tuple
from app.config import AVAILABLE_MODELS
import logging
import re

logger = logging.getLogger(__name__)


class ModelRouter:
    """智能模型路由器"""
    
    def __init__(self):
        # 模型能力矩阵
        self.model_capabilities = {
            # DeepSeek模型
            "deepseek-ai/DeepSeek-V4-Flash": {
                "speed": "fast",
                "cost": "low",
                "quality": "medium",
                "strengths": ["general", "conversation", "simple_tasks"],
                "max_tokens": 8192,
                "supports_vision": False,
                "supports_function_calling": True,
            },
            "deepseek-ai/DeepSeek-V4-Reasoner": {
                "speed": "medium",
                "cost": "medium",
                "quality": "high",
                "strengths": ["reasoning", "analysis", "complex_tasks"],
                "max_tokens": 16384,
                "supports_vision": False,
                "supports_function_calling": True,
            },
            
            # NVIDIA模型
            "meta/llama-3.1-8b-instruct": {
                "speed": "fast",
                "cost": "low",
                "quality": "medium",
                "strengths": ["general", "fast_response"],
                "max_tokens": 131072,
                "supports_vision": False,
            },
            "meta/llama-3.1-70b-instruct": {
                "speed": "medium",
                "cost": "medium",
                "quality": "high",
                "strengths": ["reasoning", "complex_tasks"],
                "max_tokens": 131072,
            },
            "meta/llama-3.2-11b-vision-instruct": {
                "speed": "medium",
                "cost": "medium",
                "quality": "high",
                "strengths": ["vision", "multimodal"],
                "max_tokens": 131072,
                "supports_vision": True,
            },
            "mistralai/mistral-large": {
                "speed": "medium",
                "cost": "high",
                "quality": "high",
                "strengths": ["reasoning", "code", "math"],
                "max_tokens": 32768,
            },
            "mistralai/mixtral-8x7b-instruct": {
                "speed": "fast",
                "cost": "low",
                "quality": "medium",
                "strengths": ["general", "multilingual"],
                "max_tokens": 32768,
            },
            "google/gemma-2-27b-it": {
                "speed": "fast",
                "cost": "low",
                "quality": "medium",
                "strengths": ["general", "safety"],
                "max_tokens": 8192,
            },
        }
        
        # 任务类型识别规则
        self.task_patterns = {
            "vision": [
                r"\.(jpg|jpeg|png|gif|webp)",
                r"图片|图像|照片|看图",
                r"image|photo|picture",
                r"识别.*图|分析.*图",
            ],
            "code": [
                r"写代码|编程|脚本|程序",
                r"code|program|script|function",
                r"\.(py|js|ts|java|cpp|go|rs)",
                r"debug|调试|修复.*错误",
                r"实现.*功能|开发",
            ],
            "math": [
                r"计算|数学|求解|方程",
                r"calculate|math|equation|solve",
                r"^\d+[\+\-\*\/]",
                r"证明|推导",
            ],
            "reasoning": [
                r"分析|推理|为什么|原因",
                r"analyze|reasoning|why|cause",
                r"比较|对比|评估",
                r"深度|详细|全面",
            ],
            "creative": [
                r"写.*故事|创作|想象",
                r"story|create|imagine|creative",
                r"设计.*方案|构思",
            ],
            "simple": [
                r"^(hi|hello|你好|嗨)$",
                r"^(是|否|ok)$",
                r"^.{1,20}$",  # 短文本
            ],
            "multilingual": [
                r"[日本語]|[한국어]|[Español]|[Français]",
            ],
        }
        
        # 路由策略
        self.routing_strategies = {
            "speed_optimized": self._route_for_speed,
            "cost_optimized": self._route_for_cost,
            "quality_optimized": self._route_for_quality,
            "balanced": self._route_balanced,
        }
    
    def detect_task_type(self, task: str, files: List[str] = None) -> List[str]:
        """检测任务类型
        
        Args:
            task: 任务文本
            files: 文件列表
        
        Returns:
            任务类型列表
        """
        task_types = []
        files = files or []
        
        # 检查文件
        for file in files:
            if re.search(r"\.(jpg|jpeg|png|gif|webp|bmp)$", file, re.I):
                task_types.append("vision")
        
        # 检查文本模式
        for task_type, patterns in self.task_patterns.items():
            for pattern in patterns:
                if re.search(pattern, task, re.I):
                    task_types.append(task_type)
                    break
        
        # 去重
        task_types = list(set(task_types))
        
        # 默认类型
        if not task_types:
            task_types.append("general")
        
        return task_types
    
    def select_model(
        self,
        task: str,
        files: List[str] = None,
        strategy: str = "balanced",
        preferred_model: str = None,
    ) -> Dict[str, Any]:
        """选择最优模型
        
        Args:
            task: 任务描述
            files: 文件列表
            strategy: 路由策略 (speed_optimized/cost_optimized/quality_optimized/balanced)
            preferred_model: 用户偏好的模型
        
        Returns:
            {
                "model": str,
                "model_id": str,
                "reasoning": str,
                "task_types": list,
                "alternative_models": list,
            }
        """
        # 如果用户指定模型，优先使用
        if preferred_model and preferred_model in AVAILABLE_MODELS.values():
            return {
                "model": preferred_model,
                "model_id": preferred_model,
                "reasoning": "User preferred model",
                "task_types": [],
                "alternative_models": [],
            }
        
        # 检测任务类型
        task_types = self.detect_task_type(task, files)
        
        # 选择路由策略
        router = self.routing_strategies.get(strategy, self._route_balanced)
        
        # 获取推荐模型
        recommended = router(task_types, task)
        
        # 获取备选模型
        alternatives = self._get_alternatives(recommended, task_types)
        
        return {
            "model": recommended,
            "model_id": recommended,
            "reasoning": self._explain_choice(recommended, task_types),
            "task_types": task_types,
            "alternative_models": alternatives,
        }
    
    def _route_for_speed(self, task_types: List[str], task: str) -> str:
        """速度优先路由"""
        # 视觉任务
        if "vision" in task_types:
            return "meta/llama-3.2-11b-vision-instruct"
        
        # 代码任务
        if "code" in task_types:
            return "deepseek-ai/DeepSeek-V4-Flash"
        
        # 简单任务
        if "simple" in task_types:
            return "meta/llama-3.1-8b-instruct"
        
        # 默认快速模型
        return "deepseek-ai/DeepSeek-V4-Flash"
    
    def _route_for_cost(self, task_types: List[str], task: str) -> str:
        """成本优先路由"""
        # 视觉任务
        if "vision" in task_types:
            return "meta/llama-3.2-11b-vision-instruct"
        
        # 默认低成本模型
        return "deepseek-ai/DeepSeek-V4-Flash"
    
    def _route_for_quality(self, task_types: List[str], task: str) -> str:
        """质量优先路由"""
        # 视觉任务
        if "vision" in task_types:
            return "meta/llama-3.2-11b-vision-instruct"
        
        # 推理任务
        if "reasoning" in task_types or "math" in task_types:
            return "deepseek-ai/DeepSeek-V4-Reasoner"
        
        # 代码任务
        if "code" in task_types:
            return "mistralai/mistral-large"
        
        # 复杂任务
        if len(task) > 500:
            return "meta/llama-3.1-70b-instruct"
        
        # 默认高质量模型
        return "deepseek-ai/DeepSeek-V4-Reasoner"
    
    def _route_balanced(self, task_types: List[str], task: str) -> str:
        """平衡路由（默认）"""
        # 视觉任务 -> 必须用视觉模型
        if "vision" in task_types:
            return "meta/llama-3.2-11b-vision-instruct"
        
        # 数学/推理 -> 推理模型
        if "math" in task_types or "reasoning" in task_types:
            # 根据任务复杂度选择
            if len(task) > 200:
                return "deepseek-ai/DeepSeek-V4-Reasoner"
            else:
                return "meta/llama-3.1-70b-instruct"
        
        # 代码任务 -> 代码优化模型
        if "code" in task_types:
            # 简单代码用快速模型
            if "简单" in task or "simple" in task.lower():
                return "deepseek-ai/DeepSeek-V4-Flash"
            else:
                return "deepseek-ai/DeepSeek-V4-Reasoner"
        
        # 简单任务 -> 快速模型
        if "simple" in task_types:
            return "meta/llama-3.1-8b-instruct"
        
        # 创作任务
        if "creative" in task_types:
            return "meta/llama-3.1-70b-instruct"
        
        # 多语言
        if "multilingual" in task_types:
            return "mistralai/mixtral-8x7b-instruct"
        
        # 默认：平衡选择
        return "deepseek-ai/DeepSeek-V4-Flash"
    
    def _get_alternatives(self, primary: str, task_types: List[str]) -> List[str]:
        """获取备选模型"""
        alternatives = []
        
        for model_id, caps in self.model_capabilities.items():
            if model_id == primary:
                continue
            
            # 检查能力匹配
            if "vision" in task_types and not caps.get("supports_vision"):
                continue
            
            # 检查是否擅长该任务
            if any(strength in caps.get("strengths", []) for strength in ["general"] + task_types):
                alternatives.append(model_id)
        
        # 最多返回3个备选
        return alternatives[:3]
    
    def _explain_choice(self, model_id: str, task_types: List[str]) -> str:
        """解释模型选择"""
        caps = self.model_capabilities.get(model_id, {})
        strengths = caps.get("strengths", [])
        
        reasons = []
        
        if "vision" in task_types and caps.get("supports_vision"):
            reasons.append("支持视觉输入")
        
        if "reasoning" in task_types and "reasoning" in strengths:
            reasons.append("擅长推理分析")
        
        if "code" in task_types and "code" in strengths:
            reasons.append("擅长代码生成")
        
        if "math" in task_types and "math" in strengths:
            reasons.append("擅长数学计算")
        
        if caps.get("speed") == "fast":
            reasons.append("响应速度快")
        
        if caps.get("cost") == "low":
            reasons.append("成本低")
        
        if not reasons:
            reasons.append("综合性能均衡")
        
        return "，".join(reasons)
    
    def get_model_stats(self) -> Dict[str, Any]:
        """获取模型统计"""
        total_models = len(self.model_capabilities)
        
        by_speed = {"fast": 0, "medium": 0, "slow": 0}
        by_cost = {"low": 0, "medium": 0, "high": 0}
        by_quality = {"low": 0, "medium": 0, "high": 0}
        
        for caps in self.model_capabilities.values():
            by_speed[caps.get("speed", "medium")] += 1
            by_cost[caps.get("cost", "medium")] += 1
            by_quality[caps.get("quality", "medium")] += 1
        
        return {
            "total_models": total_models,
            "by_speed": by_speed,
            "by_cost": by_cost,
            "by_quality": by_quality,
            "vision_models": sum(1 for c in self.model_capabilities.values() if c.get("supports_vision")),
        }


# 全局实例
_model_router = None


def get_model_router() -> ModelRouter:
    """获取全局模型路由器"""
    global _model_router
    if _model_router is None:
        _model_router = ModelRouter()
    return _model_router


def select_best_model(
    task: str,
    files: List[str] = None,
    strategy: str = "balanced",
) -> str:
    """便捷函数：选择最优模型"""
    router = get_model_router()
    result = router.select_model(task, files, strategy)
    return result["model"]
