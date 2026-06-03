"""任务规划器 - 自动分解复杂任务"""
from app.llm_client import chat_completion
from typing import Dict, Any, List, Optional
import json
import re
import logging

logger = logging.getLogger(__name__)

PLANNER_PROMPT = """You are a task planner. Break down complex tasks into a sequence of actionable steps.

Given a task, output a JSON plan with the following structure:
{
  "goal": "Overall goal description",
  "steps": [
    {
      "step": 1,
      "description": "What this step accomplishes",
      "tools": ["list of tools to use"],
      "expected_output": "What we expect to learn or produce",
    }
  ],
  "success_criteria": "How to determine if the task is complete"
}

Available tools: web_search, fetch_url, execute_code, calculate, read_file, write_file, list_directory, call_api, process_data

Rules:
- Each step should be atomic and achievable
- Steps should be ordered logically
- Include 2-8 steps for most tasks
- Be specific about what tools to use

Task: {task}"""


class TaskPlanner:
    """任务规划器 - 将复杂任务分解为步骤"""
    
    def __init__(self, model: str = None):
        self.model = model
    
    def plan(self, task: str) -> Dict[str, Any]:
        """生成任务计划
        
        Returns:
            {
                "success": bool,
                "plan": {
                    "goal": str,
                    "steps": list,
                    "success_criteria": str,
                }
            }
        """
        try:
            prompt = PLANNER_PROMPT.format(task=task)
            response = chat_completion(
                [{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.3,
            )
            
            content = response.choices[0].message.content
            
            # 提取JSON
            json_match = re.search(r'{[\s\S]+}', content)
            if json_match:
                plan = json.loads(json_match.group(0))
                return {"success": True, "plan": plan}
            else:
                return {"success": False, "error": "Failed to parse plan"}
        
        except Exception as e:
            logger.error(f"Planning failed: {e}")
            return {"success": False, "error": str(e)}
    
    def evaluate_progress(self, task: str, plan: Dict, completed_steps: List[int], results: List[Dict]) -> Dict:
        """评估进度，决定下一步
        
        Returns:
            {
                "status": "in_progress" | "completed" | "needs_revision",
                "next_step": int | None,
                "reasoning": str,
            }
        """
        try:
            prompt = f"""Task: {task}

Plan: {json.dumps(plan, ensure_ascii=False, indent=2)}

Completed steps: {completed_steps}
Results: {json.dumps(results[-3:], ensure_ascii=False, indent=2)}  # 只显示最近3个

Evaluate:
1. Are we on track?
2. What's the next step?
3. Does the plan need revision?

Output JSON:
{{"status": "in_progress|completed|needs_revision", "next_step": <number or null>, "reasoning": "<explanation>"}}
"""
            response = chat_completion(
                [{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.1,
            )
            
            content = response.choices[0].message.content
            json_match = re.search(r'{[\s\S]+}', content)
            if json_match:
                return json.loads(json_match.group(0))
            
        except Exception as e:
            logger.error(f"Progress evaluation failed: {e}")
        
        # 默认：继续下一步
        next_step = max(completed_steps) + 1 if completed_steps else 1
        return {
            "status": "in_progress",
            "next_step": next_step,
            "reasoning": "Continuing with next step",
        }
