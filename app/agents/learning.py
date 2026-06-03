"""技能学习模块 - 从用户反馈中学习"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

SKILLS_DIR = Path("E:/AgentProject/data/skills")


class SkillLearner:
    """技能学习系统"""
    
    def __init__(self):
        SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        self.skills_file = SKILLS_DIR / "learned_skills.json"
        self.feedback_file = SKILLS_DIR / "feedback_history.json"
        self._load()
    
    def _load(self):
        """加载数据"""
        if self.skills_file.exists():
            with open(self.skills_file, 'r', encoding='utf-8') as f:
                self.skills = json.load(f)
        else:
            self.skills = {}
        
        if self.feedback_file.exists():
            with open(self.feedback_file, 'r', encoding='utf-8') as f:
                self.feedback = json.load(f)
        else:
            self.feedback = []
    
    def _save(self):
        """保存数据"""
        with open(self.skills_file, 'w', encoding='utf-8') as f:
            json.dump(self.skills, f, ensure_ascii=False, indent=2)
        
        with open(self.feedback_file, 'w', encoding='utf-8') as f:
            json.dump(self.feedback, f, ensure_ascii=False, indent=2)
    
    def record_feedback(
        self,
        task: str,
        response: str,
        feedback_type: str,  # positive | negative | correction
        user_correction: str = None,
        context: Dict = None,
    ):
        """记录用户反馈
        
        Args:
            task: 原始任务
            response: Agent响应
            feedback_type: 反馈类型
            user_correction: 用户的修正内容
            context: 额外上下文
        """
        feedback_entry = {
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "response": response,
            "feedback_type": feedback_type,
            "user_correction": user_correction,
            "context": context or {},
        }
        
        self.feedback.append(feedback_entry)
        
        # 如果是修正，学习新技能
        if feedback_type == "correction" and user_correction:
            self._learn_from_correction(task, response, user_correction)
        
        # 如果是正面反馈，强化当前行为
        elif feedback_type == "positive":
            self._reinforce_behavior(task, response)
        
        self._save()
    
    def _learn_from_correction(self, task: str, wrong_response: str, correction: str):
        """从修正中学习"""
        # 提取任务模式
        pattern = self._extract_pattern(task)
        
        if pattern not in self.skills:
            self.skills[pattern] = {
                "examples": [],
                "best_practices": [],
                "avoid_patterns": [],
            }
        
        # 记录错误模式（要避免）
        self.skills[pattern]["avoid_patterns"].append({
            "wrong": wrong_response[:200],
            "correct": correction[:200],
            "learned_at": datetime.now().isoformat(),
        })
        
        # 记录最佳实践
        self.skills[pattern]["best_practices"].append(correction[:500])
        
        logger.info(f"Learned from correction for pattern: {pattern}")
    
    def _reinforce_behavior(self, task: str, response: str):
        """强化正确行为"""
        pattern = self._extract_pattern(task)
        
        if pattern not in self.skills:
            self.skills[pattern] = {
                "examples": [],
                "best_practices": [],
                "avoid_patterns": [],
            }
        
        self.skills[pattern]["examples"].append({
            "task": task[:200],
            "response": response[:500],
            "timestamp": datetime.now().isoformat(),
        })
        
        logger.info(f"Reinforced behavior for pattern: {pattern}")
    
    def _extract_pattern(self, task: str) -> str:
        """提取任务模式
        
        简单实现：基于关键词分类
        TODO: 可以用LLM做更智能的模式提取
        """
        task_lower = task.lower()
        
        # 任务类型分类
        if any(kw in task_lower for kw in ["搜索", "查找", "search", "find"]):
            return "search_task"
        elif any(kw in task_lower for kw in ["代码", "编程", "code", "写程序"]):
            return "coding_task"
        elif any(kw in task_lower for kw in ["分析", "对比", "analyze", "compare"]):
            return "analysis_task"
        elif any(kw in task_lower for kw in ["文件", "读取", "写入", "file"]):
            return "file_task"
        elif any(kw in task_lower for kw in ["计算", "统计", "calculate", "count"]):
            return "calculation_task"
        else:
            return "general_task"
    
    def get_learned_guidance(self, task: str) -> Optional[str]:
        """获取学习到的指导
        
        Returns:
            用于增强prompt的指导字符串
        """
        pattern = self._extract_pattern(task)
        
        if pattern not in self.skills:
            return None
        
        skill = self.skills[pattern]
        guidance_parts = []
        
        if skill.get("best_practices"):
            guidance_parts.append("Best practices from past experience:\n" + 
                                 "\n".join(f"- {bp[:100]}" for bp in skill["best_practices"][-3:]))
        
        if skill.get("avoid_patterns"):
            guidance_parts.append("Patterns to avoid:\n" +
                                 "\n".join(f"- Don't: {ap['wrong'][:50]}... → Do: {ap['correct'][:50]}..." 
                                          for ap in skill["avoid_patterns"][-2:]))
        
        return "\n\n".join(guidance_parts) if guidance_parts else None
    
    def get_stats(self) -> Dict:
        """获取学习统计"""
        return {
            "total_feedback": len(self.feedback),
            "positive": sum(1 for f in self.feedback if f["feedback_type"] == "positive"),
            "negative": sum(1 for f in self.feedback if f["feedback_type"] == "negative"),
            "corrections": sum(1 for f in self.feedback if f["feedback_type"] == "correction"),
            "learned_patterns": len(self.skills),
        }


# 全局实例
_skill_learner: SkillLearner = None


def get_skill_learner() -> SkillLearner:
    global _skill_learner
    if _skill_learner is None:
        _skill_learner = SkillLearner()
    return _skill_learner
