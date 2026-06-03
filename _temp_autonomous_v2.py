"""全能Agent主控 - 统一入口（完整版）"""
from app.agents.react_agent import ReactAgent
from app.agents.planner import TaskPlanner
from app.agents.reflection import SelfReflection
from app.agents.multi_agent import MultiAgentOrchestrator
from app.agents.learning import get_skill_learner
from app.agents.agents import process_message as simple_process
from app.rag.retriever import rag_retrieve
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class AutonomousAgent:
    """自主智能体 - 完整版"""
    
    def __init__(self, model: str = None, mode: str = "auto"):
        """
        Args:
            model: 模型名称
            mode: 执行模式
                - "auto": 自动选择模式
                - "simple": 单轮问答
                - "react": ReAct循环
                - "multi": 多Agent协作
        """
        self.model = model
        self.mode = mode
        self.planner = TaskPlanner(model=model)
        self.reflection = SelfReflection(model=model)
        self.multi_agent = MultiAgentOrchestrator(model=model)
        self.learner = get_skill_learner()
    
    def _detect_complexity(self, task: str) -> str:
        """检测任务复杂度"""
        # 复杂任务关键词
        complex_indicators = [
            "分析", "比较", "对比", "研究", "调研", "整理",
            "写一个", "帮我写", "创建", "生成", "构建",
            "然后", "接着", "之后", "最后", "步骤",
            "并且", "同时", "还需要", "还要",
            "analyze", "compare", "create", "build", "step",
        ]
        
        # 超复杂关键词（需要多Agent）
        multi_agent_indicators = [
            "深入研究", "全面分析", "多角度", "综合报告",
            "团队", "协作", "共同完成", "详细调研",
            "research and write", "comprehensive analysis",
        ]
        
        task_lower = task.lower()
        
        # 检查是否需要多Agent
        for indicator in multi_agent_indicators:
            if indicator in task_lower:
                return "multi"
        
        for indicator in complex_indicators:
            if indicator in task_lower:
                return "complex"
        
        return "simple"
    
    def run(
        self,
        task: str,
        context: str = "",
        history: list = None,
        enable_reflection: bool = True,
        enable_learning: bool = True,
    ) -> Dict[str, Any]:
        """执行任务
        
        Args:
            task: 用户任务
            context: 额外上下文
            history: 对话历史
            enable_reflection: 是否启用自我反思
            enable_learning: 是否使用学习到的知识
        
        Returns:
            {
                "success": bool,
                "answer": str,
                "mode": str,
                "tool_calls": list,
                "time_ms": int,
                "reflection": dict,  # 可选
                "learned_guidance": str,  # 可选
            }
        """
        import time
        start_time = time.time()
        
        # 添加RAG上下文
        rag_context = rag_retrieve(task)
        if rag_context:
            context = f"{context}\n\n[Knowledge Base]:\n{rag_context}" if context else rag_context
        
        # 添加学习到的指导
        learned_guidance = None
        if enable_learning:
            learned_guidance = self.learner.get_learned_guidance(task)
            if learned_guidance:
                context = f"{context}\n\n[Learned Experience]:\n{learned_guidance}" if context else learned_guidance
        
        # 决定执行模式
        if self.mode == "auto":
            complexity = self._detect_complexity(task)
            mode_map = {
                "simple": "simple",
                "complex": "react",
                "multi": "multi",
            }
            mode = mode_map.get(complexity, "react")
        else:
            mode = self.mode
        
        logger.info(f"Task mode: {mode}")
        
        # 执行
        if mode == "simple":
            result = simple_process(task, model=self.model, history=history)
            result["mode"] = "simple"
            result["tool_calls"] = []
        
        elif mode == "react":
            agent = ReactAgent(model=self.model, max_iterations=8, verbose=True)
            react_result = agent.run(task, context)
            result = {
                "success": react_result["success"],
                "answer": react_result["answer"],
                "mode": "react",
                "tool_calls": react_result["tool_calls"],
                "iterations": react_result["iterations"],
            }
        
        elif mode == "multi":
            multi_result = self.multi_agent.run(task, context)
            result = {
                "success": multi_result["success"],
                "answer": multi_result["answer"],
                "mode": "multi",
                "tool_calls": [],
                "agents_used": multi_result.get("agents_used", []),
                "agent_outputs": multi_result.get("agent_outputs", {}),
            }
        
        else:
            result = {
                "success": False,
                "answer": f"Unknown mode: {mode}",
                "mode": mode,
                "tool_calls": [],
            }
        
        # 自我反思
        if enable_reflection and mode != "simple":
            reflection_result = self.reflection.should_retry(
                task=task,
                response=result["answer"],
                tool_calls=result.get("tool_calls", []),
                previous_attempts=0,
                max_attempts=1,
            )
            result["reflection"] = {
                "passed": not reflection_result.get("retry", False),
                "score": reflection_result.get("evaluation", {}).get("overall", 7),
                "issues": reflection_result.get("evaluation", {}).get("issues", []),
            }
        
        result["time_ms"] = int((time.time() - start_time) * 1000)
        
        if learned_guidance:
            result["learned_guidance"] = "Applied learned experience"
        
        return result


def run_agent(
    task: str,
    model: str = None,
    mode: str = "auto",
    context: str = "",
    history: list = None,
    **kwargs,
) -> Dict:
    """运行全能Agent（便捷函数）"""
    agent = AutonomousAgent(model=model, mode=mode)
    return agent.run(task, context=context, history=history, **kwargs)
