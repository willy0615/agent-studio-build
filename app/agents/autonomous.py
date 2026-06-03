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
            "写", "编写", "创建", "生成", "构建", "开发",
            "然后", "接着", "之后", "最后", "步骤",
            "并且", "同时", "还需要", "还要",
            "搜索", "查找", "获取", "读取", "下载",
            "计算", "处理", "转换", "分析数据",
            "analyze", "compare", "create", "build", "step",
            "search", "find", "fetch", "calculate", "write",
            "program", "code", "script",
        ]
        
        # 超复杂关键词（需要多Agent）
        multi_agent_indicators = [
            "深入研究", "全面分析", "多角度", "综合报告",
            "团队", "协作", "共同完成", "详细调研",
            "深度研究", "详细分析", "系统研究",
            "research and write", "comprehensive analysis",
            "deep research", "thorough analysis",
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
                "plan_progress": dict,  # 可选，计划执行进度
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
            simple_result = simple_process(task, model=self.model, history=history)
            result = {
                "success": True,
                "answer": simple_result["response"],
                "mode": "simple",
                "tool_calls": [],
                "agent": simple_result.get("agent", "general"),
            }
        
        elif mode == "react":
            # 先用Planner分解复杂任务
            plan = None
            plan_steps = []
            
            # 检查任务是否足够复杂需要规划
            if len(task) > 50 or any(kw in task.lower() for kw in ["分析", "研究", "报告", "步骤", "然后", "and", "then", "analyze", "research"]):
                plan_result = self.planner.plan(task)
                if plan_result["success"]:
                    plan = plan_result["plan"]
                    plan_steps = plan.get("steps", [])
                    logger.info(f"Task planned into {len(plan_steps)} steps")
            
            # 执行ReAct
            agent = ReactAgent(model=self.model, max_iterations=8, verbose=True)
            
            # 如果有计划，添加计划上下文
            if plan_steps:
                plan_context = f"\n\n[Task Plan]:\nGoal: {plan['goal']}\n"
                for step in plan_steps:
                    plan_context += f"Step {step['step']}: {step['description']}\n"
                plan_context += f"\nSuccess Criteria: {plan['success_criteria']}\n"
                context = f"{context}{plan_context}" if context else plan_context
            
            react_result = agent.run(task, context)
            all_tool_calls = react_result.get("tool_calls", [])
            
            # ===== 集成 Planner 进度评估 =====
            plan_progress = None
            if plan and plan_steps:
                completed_steps = list(range(1, len(plan_steps) + 1))
                step_results = [{"answer": react_result["answer"], "tool_calls": all_tool_calls}]
                try:
                    progress = self.planner.evaluate_progress(
                        task=task, plan=plan,
                        completed_steps=completed_steps, results=step_results,
                    )
                    plan_progress = {
                        "status": progress.get("status", "in_progress"),
                        "reasoning": progress.get("reasoning", ""),
                        "next_step": progress.get("next_step"),
                    }
                    logger.info(f"Plan progress: status={plan_progress['status']}, "
                                f"reasoning={plan_progress['reasoning']}")
                    
                    # 如果计划需要修订，追加修订说明到结果
                    if progress.get("status") == "needs_revision":
                        revision_note = f"\n\n⚠️ 计划执行评估：{progress.get('reasoning', '需要调整')}"
                        react_result["answer"] += revision_note
                except Exception as e:
                    logger.warning(f"Progress evaluation failed: {e}")
            
            result = {
                "success": react_result["success"],
                "answer": react_result["answer"],
                "mode": "react",
                "tool_calls": all_tool_calls,
                "iterations": react_result["iterations"],
                "plan": plan,
                "plan_progress": plan_progress,
            }
            # 记录工具调用统计
            from app.utils.stats import get_stats
            stats = get_stats()
            for tc in all_tool_calls:
                stats.record_agent_call(tc.get("tool", "unknown"))
        
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
            # 记录Agent调用统计
            from app.utils.stats import get_stats
            stats = get_stats()
            for agent_name in multi_result.get("agents_used", []):
                stats.record_agent_call(agent_name)
        
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
    
    
    def run_stream(
        self,
        task: str,
        context: str = "",
        history: list = None,
        **kwargs,
    ):
        """流式执行任务（仅Simple模式支持流式）"""
        from app.llm_client import chat_stream
        
        effective_mode = kwargs.get("mode", self.mode)
        if effective_mode not in ("simple", "auto"):
            logger.warning(f"Streaming only supports simple mode, ignoring mode={effective_mode}")
        
        # 添加RAG上下文
        rag_context = rag_retrieve(task)
        if rag_context and not rag_context.startswith("[RAG Error"):
            context = f"{context}\n\n[Knowledge Base]:\n{rag_context}" if context else rag_context
        
        # 添加学习指导
        learned_guidance = self.learner.get_learned_guidance(task)
        if learned_guidance:
            context = f"{context}\n\n[Learned Experience]:\n{learned_guidance}" if context else learned_guidance
        
        # 构建消息
        messages = []
        if history:
            messages.extend(history)
        if context:
            messages.append({"role": "system", "content": context})
        messages.append({"role": "user", "content": task})
        
        # 流式输出
        for chunk in chat_stream(messages, model=self.model):
            yield chunk


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


def run_agent_stream(
    task: str,
    model: str = None,
    mode: str = "auto",
    context: str = "",
    history: list = None,
    **kwargs,
):
    """流式运行全能Agent（便捷函数）"""
    agent = AutonomousAgent(model=model, mode=mode)
    return agent.run_stream(task, context=context, history=history, **kwargs)
