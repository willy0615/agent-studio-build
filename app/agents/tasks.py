"""任务持久化 - 后台任务和定时任务"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import threading
import time
import logging

logger = logging.getLogger(__name__)

TASKS_DIR = Path("E:/AgentProject/data/tasks")


class TaskPersistence:
    """任务持久化管理"""
    
    def __init__(self):
        TASKS_DIR.mkdir(parents=True, exist_ok=True)
        self.tasks_file = TASKS_DIR / "tasks.json"
        self._load()
    
    def _load(self):
        """加载任务数据"""
        if self.tasks_file.exists():
            with open(self.tasks_file, 'r', encoding='utf-8') as f:
                self.tasks = json.load(f)
        else:
            self.tasks = {"active": [], "completed": [], "scheduled": []}
    
    def _save(self):
        """保存任务数据"""
        with open(self.tasks_file, 'w', encoding='utf-8') as f:
            json.dump(self.tasks, f, ensure_ascii=False, indent=2)
    
    def create_task(
        self,
        task: str,
        mode: str = "immediate",
        schedule: str = None,
        priority: str = "normal",
        metadata: Dict = None,
    ) -> Dict[str, Any]:
        """创建任务
        
        Args:
            task: 任务描述
            mode: immediate | background | scheduled
            schedule: 定时表达式 (cron格式或自然语言)
            priority: low | normal | high | urgent
            metadata: 额外元数据
        
        Returns:
            任务对象
        """
        task_obj = {
            "id": f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(task) % 10000}",
            "task": task,
            "mode": mode,
            "priority": priority,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "schedule": schedule,
            "metadata": metadata or {},
            "result": None,
            "error": None,
        }
        
        if mode == "scheduled":
            self.tasks["scheduled"].append(task_obj)
        else:
            self.tasks["active"].append(task_obj)
        
        self._save()
        return task_obj
    
    def update_task(self, task_id: str, **updates):
        """更新任务"""
        for category in ["active", "completed", "scheduled"]:
            for task in self.tasks[category]:
                if task["id"] == task_id:
                    task.update(updates)
                    task["updated_at"] = datetime.now().isoformat()
                    self._save()
                    return task
        return None
    
    def complete_task(self, task_id: str, result: str, error: str = None):
        """标记任务完成"""
        for task in self.tasks["active"]:
            if task["id"] == task_id:
                task["status"] = "completed"
                task["result"] = result
                task["error"] = error
                task["completed_at"] = datetime.now().isoformat()
                self.tasks["completed"].append(task)
                self.tasks["active"].remove(task)
                self._save()
                return task
        return None
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """获取任务"""
        for category in ["active", "completed", "scheduled"]:
            for task in self.tasks[category]:
                if task["id"] == task_id:
                    return task
        return None
    
    def list_tasks(self, status: str = None, limit: int = 20) -> List[Dict]:
        """列出任务"""
        result = []
        
        if status in [None, "active"]:
            result.extend(self.tasks["active"])
        if status in [None, "scheduled"]:
            result.extend(self.tasks["scheduled"])
        if status in [None, "completed"]:
            result.extend(self.tasks["completed"][-limit//2:])
        
        # 按时间排序
        result.sort(key=lambda x: x["created_at"], reverse=True)
        return result[:limit]
    
    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        for category in ["active", "completed", "scheduled"]:
            for i, task in enumerate(self.tasks[category]):
                if task["id"] == task_id:
                    self.tasks[category].pop(i)
                    self._save()
                    return True
        return False
    
    def get_stats(self) -> Dict:
        """获取任务统计"""
        return {
            "active": len(self.tasks["active"]),
            "completed": len(self.tasks["completed"]),
            "scheduled": len(self.tasks["scheduled"]),
        }


# 全局实例
_task_persistence: TaskPersistence = None


def get_task_manager() -> TaskPersistence:
    global _task_persistence
    if _task_persistence is None:
        _task_persistence = TaskPersistence()
    return _task_persistence
