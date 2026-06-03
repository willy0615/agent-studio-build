"""自我反思模块 - 评估执行质量并决定是否重试"""
from app.llm_client import chat_completion
from typing import Dict, Any, List
import json
import re
import logging

logger = logging.getLogger(__name__)

REFLECTION_PROMPT = """You are a quality evaluator. Assess if the task was completed successfully.

**Task**: {task}

**Agent Response**: {response}

**Tool Calls**: {tool_calls}

Evaluate:
1. **Completeness**: Did the agent fully address the task? (1-10)
2. **Accuracy**: Is the information correct and verifiable? (1-10)
3. **Actionability**: Can the user act on this response? (1-10)
4. **Clarity**: Is the response clear and well-structured? (1-10)

Output JSON:
{
  "scores": {
    "completeness": <1-10>,
    "accuracy": <1-10>,
    "actionability": <1-10>,
    "clarity": <1-10>
  },
  "overall": <average score>,
  "passed": <true if overall >= 7>,
  "issues": ["list of problems if any"],
  "improvement_suggestions": ["how to improve if score < 7"]
}
"""


class SelfReflection:
    """自我反思 - 评估执行质量"""
    
    def __init__(self, threshold: float = 7.0, model: str = None):
        self.threshold = threshold
        self.model = model
    
    def evaluate(
        self,
        task: str,
        response: str,
        tool_calls: List[Dict] = None,
    ) -> Dict[str, Any]:
        """评估任务执行质量
        
        Returns:
            {
                "passed": bool,
                "scores": dict,
                "overall": float,
                "issues": list,
                "suggestions": list,
            }
        """
        try:
            prompt = REFLECTION_PROMPT.format(
                task=task,
                response=response[:2000],  # 限制长度
                tool_calls=json.dumps(tool_calls or [], ensure_ascii=False),
            )
            
            result = chat_completion(
                [{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.3,
            )
            
            content = result.choices[0].message.content
            
            # 解析JSON
            json_match = re.search(r'{[\s\S]+}', content)
            if json_match:
                evaluation = json.loads(json_match.group(0))
                
                return {
                    "passed": evaluation.get("overall", 0) >= self.threshold,
                    "scores": evaluation.get("scores", {}),
                    "overall": evaluation.get("overall", 0),
                    "issues": evaluation.get("issues", []),
                    "suggestions": evaluation.get("improvement_suggestions", []),
                }
        
        except Exception as e:
            logger.error(f"Reflection failed: {e}")
        
        # 默认通过
        return {
            "passed": True,
            "scores": {},
            "overall": 7.0,
            "issues": [],
            "suggestions": [],
        }
    
    def should_retry(
        self,
        task: str,
        response: str,
        tool_calls: List[Dict],
        previous_attempts: int = 0,
        max_attempts: int = 2,
    ) -> Dict[str, Any]:
        """判断是否应该重试
        
        Returns:
            {
                "retry": bool,
                "reason": str,
                "improved_prompt": str,  # 改进后的提示
            }
        """
        if previous_attempts >= max_attempts:
            return {"retry": False, "reason": "Max attempts reached"}
        
        evaluation = self.evaluate(task, response, tool_calls)
        
        if evaluation["passed"]:
            return {
                "retry": False,
                "reason": f"Quality passed (score: {evaluation['overall']})",
            }
        
        # 构建改进提示
        issues = evaluation.get("issues", [])
        suggestions = evaluation.get("suggestions", [])
        
        improved_prompt = f"""Previous attempt had issues: {', '.join(issues)}

Suggestions for improvement: {', '.join(suggestions)}

Original task: {task}

Please try again with better quality. Focus on addressing the issues above."""
        
        return {
            "retry": True,
            "reason": f"Quality below threshold (score: {evaluation['overall']})",
            "improved_prompt": improved_prompt,
            "evaluation": evaluation,
        }
