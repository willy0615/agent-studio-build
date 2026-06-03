"""多Agent协作系统 - 增强版"""
from app.llm_client import chat_completion, chat_stream
from app.agents.planner import TaskPlanner
from app.agents.react_agent import ReactAgent
from app.agents.reflection import SelfReflection
from typing import Dict, Any, List, Optional
import json
import time
import logging
import re

logger = logging.getLogger(__name__)

# Agent角色定义
AGENT_ROLES = {
    "coordinator": {
        "name": "Coordinator",
        "description": "协调多个Agent，分配任务，整合结果",
        "system_prompt": """你是协调者，负责：
1. 理解任务目标
2. 分配子任务给合适的专家
3. 整合各专家的输出
4. 确保最终交付质量

你有以下专家可用：
- researcher: 研究员，负责信息收集和调研
- coder: 程序员，负责写代码和数据处理
- analyst: 分析师，负责逻辑分析和报告生成
- reviewer: 审核员，负责质量检查

输出格式：
{"assign": ["agent1", "agent2"], "tasks": {"agent1": "任务描述", "agent2": "任务描述"}}""",
    },
    
    "researcher": {
        "name": "Researcher",
        "description": "信息收集专家，擅长搜索、阅读、整理",
        "system_prompt": """你是研究员，负责收集和整理信息。
- 使用web_search搜索信息
- 使用fetch_url获取详细内容
- 输出结构化的调研结果
- 标注信息来源""",
    },
    
    "coder": {
        "name": "Coder",
        "description": "编程专家，擅长写代码、处理数据、自动化任务",
        "system_prompt": """你是程序员，负责：
- 编写Python代码解决问题
- 执行代码并验证结果
- 处理数据文件（CSV、JSON等）
- 创建自动化脚本
确保代码可运行、有注释、输出清晰。""",
    },
    
    "analyst": {
        "name": "Analyst",
        "description": "分析专家，擅长逻辑推理、数据洞察、报告生成",
        "system_prompt": """你是分析师，负责：
- 逻辑推理和因果分析
- 数据洞察和趋势预测
- 生成结构化报告
- 提供可执行建议
输出要有数据支撑、逻辑清晰、结论明确。""",
    },
    
    "reviewer": {
        "name": "Reviewer",
        "description": "审核专家，负责质量检查和错误修正",
        "system_prompt": """你是审核员，负责：
- 检查其他Agent的输出质量
- 发现错误和不一致
- 提出改进建议
- 验证事实准确性

输出格式：
{"passed": true/false, "issues": ["问题列表"], "suggestions": ["改进建议"]}""",
    },
}


class MultiAgentOrchestrator:
    """多Agent协调器 - 增强版"""
    
    def __init__(self, model: str = None):
        self.model = model
        self.planner = TaskPlanner(model=model)
        self.reflection = SelfReflection(model=model)
        self.agents = AGENT_ROLES  # Expose for testing
        self.workflow = ["coordinator", "researcher", "coder", "analyst", "reviewer"]
    
    def _run_single_agent(
        self,
        role: str,
        task: str,
        context: str = "",
    ) -> Dict[str, Any]:
        """运行单个Agent"""
        agent_config = AGENT_ROLES.get(role)
        if not agent_config:
            return {"error": f"Unknown role: {role}"}
        
        messages = [
            {"role": "system", "content": agent_config["system_prompt"]},
            {"role": "user", "content": f"{context}\n\nTask: {task}" if context else task},
        ]
        
        try:
            # 使用ReAct风格
            agent = ReactAgent(model=self.model, max_iterations=6, verbose=False)
            result = agent.run(task, context)
            
            return {
                "role": role,
                "success": True,
                "output": result["answer"],
                "tool_calls": result.get("tool_calls", []),
            }
        
        except Exception as e:
            logger.error(f"Agent {role} failed: {e}")
            return {
                "role": role,
                "success": False,
                "error": str(e),
            }
    
    def _smart_assign(self, task: str) -> Dict[str, Any]:
        """智能分配Agent（基于任务特征）"""
        task_lower = task.lower()
        
        # 研究类任务
        if any(kw in task_lower for kw in ["研究", "调研", "调查", "research", "investigate", "survey"]):
            return {"assign": ["researcher", "analyst"], "tasks": {}}
        
        # 代码类任务
        elif any(kw in task_lower for kw in ["写代码", "编程", "脚本", "code", "program", "script", "python"]):
            return {"assign": ["coder", "reviewer"], "tasks": {}}
        
        # 分析类任务
        elif any(kw in task_lower for kw in ["分析", "报告", "洞察", "analyze", "report", "insight"]):
            return {"assign": ["researcher", "analyst", "reviewer"], "tasks": {}}
        
        # 数据类任务
        elif any(kw in task_lower for kw in ["数据", "excel", "csv", "data", "统计"]):
            return {"assign": ["coder", "analyst"], "tasks": {}}
        
        # 默认：研究员 + 分析师
        else:
            return {"assign": ["researcher", "analyst"], "tasks": {}}
    
    def run(self, task: str, context: str = "") -> Dict[str, Any]:
        """执行多Agent协作 - 增强版
        
        Returns:
            {
                "success": bool,
                "answer": str,
                "agents_used": list,
                "agent_outputs": dict,
                "iterations": int,
                "time_ms": int,
                "plan": dict,  # 新增：任务规划
            }
        """
        start_time = time.time()
        
        # 1. 使用Planner先规划
        logger.info("Step 0: Planning task decomposition...")
        plan = None
        
        try:
            plan_result = self.planner.plan(task)
            if plan_result["success"]:
                plan = plan_result["plan"]
                plan_context = f"\n[Task Plan]\nGoal: {plan['goal']}\nSteps: {len(plan['steps'])}\n"
                context = f"{context}{plan_context}" if context else plan_context
        except Exception as e:
            logger.warning(f"Planning failed: {e}")
        
        # 2. 协调者分析任务，分配工作
        logger.info("Step 1: Coordinator analyzing task...")
        coord_result = self._run_single_agent("coordinator", task, context)
        
        if not coord_result["success"]:
            # 回退到单Agent
            logger.warning("Coordinator failed, falling back to single agent")
            single_agent = ReactAgent(model=self.model)
            return single_agent.run(task, context)
        
        # 解析分配方案
        try:
            assign_match = coord_result["output"]
            # 尝试提取JSON
            json_match = re.search(r'{[\s\S]+}', assign_match)
            if json_match:
                assignment = json.loads(json_match.group(0))
            else:
                # 智能默认分配
                assignment = self._smart_assign(task)
        except:
            assignment = self._smart_assign(task)
        
        agents_to_run = assignment.get("assign", ["researcher"])
        tasks_by_agent = assignment.get("tasks", {})
        
        logger.info(f"Assigned agents: {agents_to_run}")
        
        # 3. 执行各Agent（带上下文传递）
        agent_outputs = {}
        accumulated_context = context
        agents_used = []
        
        for role in agents_to_run:
            if role == "coordinator":
                continue
            
            # 获取该Agent的子任务
            subtask = tasks_by_agent.get(role, task)
            logger.info(f"Running {role}...")
            
            # 运行Agent
            result = self._run_single_agent(role, subtask, accumulated_context)
            agent_outputs[role] = result
            
            if result["success"]:
                agents_used.append(role)
                # 将输出添加到累积上下文
                accumulated_context += f"\n\n[{role.upper()} OUTPUT]:\n{result['output'][:500]}"
            else:
                logger.warning(f"{role} failed: {result.get('error')}")
        
        # 4. 审核员检查（可选）
        if len(agents_used) > 1:
            logger.info("Step 2: Reviewer checking quality...")
            review_context = accumulated_context + f"\n\nOriginal Task: {task}"
            review_result = self._run_single_agent("reviewer", "检查上述输出的质量", review_context)
            
            if review_result["success"]:
                agent_outputs["reviewer"] = review_result
                
                # 解析审核结果
                try:
                    review_json = json.loads(re.search(r'{[\s\S]+}', review_result["output"]).group(0))
                    if not review_json.get("passed", True):
                        logger.warning(f"Review failed: {review_json.get('issues')}")
                except:
                    pass
        
        # 5. 整合最终答案
        logger.info("Step 3: Synthesizing final answer...")
        
        # 提取主要输出
        main_output = ""
        for role in ["analyst", "researcher", "coder"]:
            if role in agent_outputs and agent_outputs[role]["success"]:
                main_output = agent_outputs[role]["output"]
                break
        
        if not main_output:
            main_output = "抱歉，Agent协作未能完成任务。"
        
        elapsed_time = int((time.time() - start_time) * 1000)
        
        return {
            "success": True,
            "answer": main_output,
            "agents_used": agents_used,
            "agent_outputs": {k: v["output"][:200] for k, v in agent_outputs.items() if v.get("success")},
            "iterations": len(agents_used),
            "time_ms": elapsed_time,
            "plan": plan,
        }


def get_multi_agent_orchestrator(model: str = None) -> MultiAgentOrchestrator:
    """获取Multi-Agent协调器实例"""
    return MultiAgentOrchestrator(model=model)
