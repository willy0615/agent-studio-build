"""任务调度系统 - 定时执行、后台任务"""
from typing import Dict, Any, Callable, Optional
from datetime import datetime, timedelta
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, storage_dir: str = None):
        """
        Args:
            storage_dir: 任务存储目录
        """
        self.storage_dir = Path(storage_dir or "E:/AgentProject/data/scheduled_tasks")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.tasks = {}
        self.job_queue = []
        self._load_tasks()
    
    def _load_tasks(self):
        """加载已保存的任务"""
        task_file = self.storage_dir / "scheduled_tasks.json"
        if task_file.exists():
            try:
                with open(task_file, "r", encoding="utf-8") as f:
                    self.tasks = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load tasks: {e}")
    
    def _save_tasks(self):
        """保存任务"""
        task_file = self.storage_dir / "scheduled_tasks.json"
        try:
            with open(task_file, "w", encoding="utf-8") as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save tasks: {e}")
    
    def schedule_task(
        self,
        task_id: str,
        task_func: Callable,
        execute_at: datetime = None,
        delay_seconds: int = None,
        cron_expr: str = None,
        repeat: bool = False,
        task_description: str = "",
    ) -> Dict[str, Any]:
        """
        调度任务
        
        Args:
            task_id: 任务ID
            task_func: 要执行的函数
            execute_at: 执行时间
            delay_seconds: 延迟秒数
            cron_expr: Cron表达式
            repeat: 是否重复
            task_description: 任务描述
        
        Returns:
            调度结果
        """
        # 计算执行时间
        if execute_at:
            scheduled_time = execute_at
        elif delay_seconds:
            scheduled_time = datetime.now() + timedelta(seconds=delay_seconds)
        elif cron_expr:
            scheduled_time = self._parse_cron(cron_expr)
        else:
            return {
                "success": False,
                "error": "Must specify execute_at, delay_seconds, or cron_expr",
            }
        
        # 创建任务记录
        task_record = {
            "id": task_id,
            "description": task_description,
            "scheduled_time": scheduled_time.isoformat(),
            "cron_expr": cron_expr,
            "repeat": repeat,
            "status": "scheduled",
            "created_at": datetime.now().isoformat(),
        }
        
        self.tasks[task_id] = task_record
        self._save_tasks()
        
        # 添加到队列
        self.job_queue.append({
            "id": task_id,
            "func": task_func,
            "scheduled_time": scheduled_time,
            "repeat": repeat,
        })
        
        logger.info(f"Scheduled task: {task_id} at {scheduled_time}")
        
        return {
            "success": True,
            "task_id": task_id,
            "scheduled_time": scheduled_time.isoformat(),
        }
    
    def schedule_reminder(
        self,
        message: str,
        delay_minutes: int,
        notification_type: str = "desktop",
    ) -> Dict[str, Any]:
        """
        调度提醒
        
        Args:
            message: 提醒内容
            delay_minutes: 延迟分钟数
            notification_type: 通知类型 (desktop, email, webhook)
        """
        task_id = f"reminder_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        def send_reminder():
            if notification_type == "desktop":
                from app.tools.notifications import send_desktop_notification
                send_desktop_notification("⏰ 提醒", message)
            elif notification_type == "email":
                from app.tools.notifications import send_email
                # 需要配置邮件
                logger.warning("Email notification requires configuration")
            elif notification_type == "webhook":
                logger.warning("Webhook notification requires configuration")
        
        return self.schedule_task(
            task_id=task_id,
            task_func=send_reminder,
            delay_seconds=delay_minutes * 60,
            task_description=f"Reminder: {message}",
        )
    
    def schedule_periodic_report(
        self,
        report_func: Callable,
        cron_expr: str,
        report_name: str,
    ) -> Dict[str, Any]:
        """
        调度周期性报告
        
        Args:
            report_func: 报告生成函数
            cron_expr: Cron表达式
            report_name: 报告名称
        """
        task_id = f"report_{report_name}_{datetime.now().strftime('%Y%m%d')}"
        
        return self.schedule_task(
            task_id=task_id,
            task_func=report_func,
            cron_expr=cron_expr,
            repeat=True,
            task_description=f"Periodic report: {report_name}",
        )
    
    def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """取消任务"""
        if task_id in self.tasks:
            self.tasks[task_id]["status"] = "cancelled"
            self._save_tasks()
            
            # 从队列中移除
            self.job_queue = [j for j in self.job_queue if j["id"] != task_id]
            
            logger.info(f"Cancelled task: {task_id}")
            return {"success": True}
        
        return {"success": False, "error": "Task not found"}
    
    def check_and_execute(self) -> list:
        """检查并执行到期任务"""
        now = datetime.now()
        executed = []
        
        for job in self.job_queue[:]:
            if job["scheduled_time"] <= now:
                try:
                    logger.info(f"Executing task: {job['id']}")
                    job["func"]()
                    
                    # 更新状态
                    if job["id"] in self.tasks:
                        self.tasks[job["id"]]["status"] = "completed"
                        self.tasks[job["id"]]["executed_at"] = now.isoformat()
                    
                    executed.append(job["id"])
                    
                    # 如果是重复任务，重新调度
                    if job["repeat"]:
                        # TODO: 根据cron表达式计算下次执行时间
                        pass
                    else:
                        self.job_queue.remove(job)
                
                except Exception as e:
                    logger.error(f"Failed to execute task {job['id']}: {e}")
                    if job["id"] in self.tasks:
                        self.tasks[job["id"]]["status"] = "failed"
                        self.tasks[job["id"]]["error"] = str(e)
        
        if executed:
            self._save_tasks()
        
        return executed
    
    def list_scheduled_tasks(self) -> list:
        """列出所有已调度任务"""
        return [
            {
                "id": task_id,
                "description": task.get("description"),
                "scheduled_time": task.get("scheduled_time"),
                "status": task.get("status"),
                "repeat": task.get("repeat"),
            }
            for task_id, task in self.tasks.items()
        ]
    
    @staticmethod
    def _parse_cron(cron_expr: str) -> datetime:
        """
        解析Cron表达式（简化版）
        格式: minute hour day month weekday
        例如: "0 9 * * *" 表示每天9点
        """
        parts = cron_expr.split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {cron_expr}")
        
        minute, hour, day, month, weekday = parts
        
        now = datetime.now()
        
        # 简化处理：只处理基本的每天定时
        if minute != "*" and hour != "*":
            scheduled = now.replace(
                minute=int(minute),
                hour=int(hour),
                second=0,
                microsecond=0,
            )
            
            # 如果时间已过，安排到明天
            if scheduled <= now:
                scheduled += timedelta(days=1)
            
            return scheduled
        
        # 默认1小时后
        return now + timedelta(hours=1)


# 常用Cron表达式
CRON_PRESETS = {
    "every_minute": "* * * * *",
    "hourly": "0 * * * *",
    "daily_9am": "0 9 * * *",
    "daily_6pm": "0 18 * * *",
    "weekly_monday": "0 9 * * 1",
    "monthly_first": "0 9 1 * *",
}


# 全局调度器实例
_scheduler = None


def get_scheduler() -> TaskScheduler:
    """获取全局调度器实例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskScheduler()
    return _scheduler
