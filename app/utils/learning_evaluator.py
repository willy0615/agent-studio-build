"""学习效果评估 - 量化Agent学习和改进效果"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)


class LearningEvaluator:
    """学习效果评估器"""
    
    def __init__(self):
        # 学习记录
        self.learning_records = []
        
        # 性能指标
        self.metrics = {
            "task_success_rate": [],
            "tool_usage_efficiency": [],
            "response_quality": [],
            "error_rate": [],
            "user_satisfaction": [],
        }
        
        # 改进历史
        self.improvements = []
    
    def record_task_execution(
        self,
        task: str,
        success: bool,
        execution_time_ms: int,
        tool_calls: List[Dict] = None,
        error: str = None,
        user_feedback: str = None,
    ):
        """记录任务执行
        
        Args:
            task: 任务描述
            success: 是否成功
            execution_time_ms: 执行时间（毫秒）
            tool_calls: 工具调用列表
            error: 错误信息（如果有）
            user_feedback: 用户反馈
        """
        record = {
            "timestamp": datetime.now().isoformat(),
            "task": task[:100],  # 截断长任务
            "success": success,
            "execution_time_ms": execution_time_ms,
            "tool_calls": tool_calls or [],
            "tool_count": len(tool_calls) if tool_calls else 0,
            "error": error,
            "user_feedback": user_feedback,
        }
        
        self.learning_records.append(record)
        
        # 更新指标
        self._update_metrics(record)
    
    def _update_metrics(self, record: Dict):
        """更新性能指标"""
        # 成功率
        self.metrics["task_success_rate"].append(1 if record["success"] else 0)
        
        # 工具使用效率（成功任务的平均工具调用数）
        if record["success"] and record["tool_count"] > 0:
            self.metrics["tool_usage_efficiency"].append(record["tool_count"])
        
        # 错误率
        self.metrics["error_rate"].append(1 if record["error"] else 0)
        
        # 用户满意度（基于反馈）
        if record["user_feedback"]:
            satisfaction = self._parse_feedback(record["user_feedback"])
            self.metrics["user_satisfaction"].append(satisfaction)
    
    def _parse_feedback(self, feedback: str) -> float:
        """解析用户反馈为满意度分数（0-1）"""
        feedback_lower = feedback.lower()
        
        # 正面反馈
        positive_words = ["好", "棒", "优秀", "完美", "thanks", "good", "great", "excellent", "perfect"]
        # 负面反馈
        negative_words = ["差", "糟", "错误", "不对", "bad", "wrong", "error", "fail"]
        
        positive_count = sum(1 for word in positive_words if word in feedback_lower)
        negative_count = sum(1 for word in negative_words if word in feedback_lower)
        
        if positive_count > negative_count:
            return 1.0
        elif negative_count > positive_count:
            return 0.0
        else:
            return 0.5
    
    def evaluate_learning(self, days: int = 7) -> Dict[str, Any]:
        """评估学习效果
        
        Args:
            days: 评估周期（天）
        
        Returns:
            {
                "period_days": int,
                "total_tasks": int,
                "success_rate": float,
                "avg_execution_time": float,
                "improvement_trends": dict,
                "recommendations": list,
            }
        """
        # 筛选时间范围内的记录
        cutoff = datetime.now() - timedelta(days=days)
        recent_records = [
            r for r in self.learning_records
            if datetime.fromisoformat(r["timestamp"]) > cutoff
        ]
        
        if not recent_records:
            return {
                "period_days": days,
                "total_tasks": 0,
                "message": "无足够数据进行评估",
            }
        
        # 计算总体指标
        total_tasks = len(recent_records)
        successful_tasks = sum(1 for r in recent_records if r["success"])
        success_rate = successful_tasks / total_tasks
        
        avg_time = sum(r["execution_time_ms"] for r in recent_records) / total_tasks
        
        # 计算趋势（对比前一周）
        trends = self._calculate_trends(days)
        
        # 生成建议
        recommendations = self._generate_recommendations(recent_records, trends)
        
        return {
            "period_days": days,
            "total_tasks": total_tasks,
            "success_rate": round(success_rate * 100, 2),
            "avg_execution_time_ms": round(avg_time, 2),
            "improvement_trends": trends,
            "recommendations": recommendations,
            "metrics_summary": {
                "total_tool_calls": sum(r["tool_count"] for r in recent_records),
                "error_count": sum(1 for r in recent_records if r["error"]),
                "feedback_count": sum(1 for r in recent_records if r["user_feedback"]),
            },
        }
    
    def _calculate_trends(self, days: int) -> Dict[str, Any]:
        """计算改进趋势"""
        if len(self.learning_records) < 10:
            return {"status": "insufficient_data"}
        
        # 分割为两个时段
        cutoff = datetime.now() - timedelta(days=days)
        recent = [r for r in self.learning_records if datetime.fromisoformat(r["timestamp"]) > cutoff]
        previous = [r for r in self.learning_records if datetime.fromisoformat(r["timestamp"]) <= cutoff]
        
        if not recent or not previous:
            return {"status": "insufficient_data"}
        
        # 计算成功率变化
        recent_success = sum(1 for r in recent if r["success"]) / len(recent)
        previous_success = sum(1 for r in previous if r["success"]) / len(previous)
        
        success_change = recent_success - previous_success
        
        # 计算执行时间变化
        recent_time = sum(r["execution_time_ms"] for r in recent) / len(recent)
        previous_time = sum(r["execution_time_ms"] for r in previous) / len(previous)
        
        time_change = previous_time - recent_time  # 负数表示变慢
        
        return {
            "success_rate_change": round(success_change * 100, 2),
            "execution_time_change_ms": round(time_change, 2),
            "direction": "improving" if success_change > 0 else "declining" if success_change < 0 else "stable",
        }
    
    def _generate_recommendations(
        self,
        records: List[Dict],
        trends: Dict,
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 成功率分析
        success_rate = sum(1 for r in records if r["success"]) / len(records)
        
        if success_rate < 0.7:
            recommendations.append("成功率较低，建议检查常见错误模式并优化")
        
        # 错误分析
        errors = [r["error"] for r in records if r["error"]]
        if errors:
            error_types = {}
            for error in errors:
                error_type = error.split(":")[0] if ":" in error else "unknown"
                error_types[error_type] = error_types.get(error_type, 0) + 1
            
            most_common_error = max(error_types, key=error_types.get)
            recommendations.append(f"最常见错误: {most_common_error}，建议针对性优化")
        
        # 工具使用分析
        tool_usage = {}
        for r in records:
            for tc in r.get("tool_calls", []):
                tool_name = tc.get("tool", "unknown")
                tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1
        
        if tool_usage:
            most_used_tool = max(tool_usage, key=tool_usage.get)
            recommendations.append(f"最常用工具: {most_used_tool}，可考虑优化其性能")
        
        # 执行时间分析
        slow_tasks = [r for r in records if r["execution_time_ms"] > 10000]
        if slow_tasks:
            recommendations.append(f"发现 {len(slow_tasks)} 个慢任务（>10秒），建议优化")
        
        # 趋势分析
        if trends.get("direction") == "declining":
            recommendations.append("性能呈下降趋势，建议检查最近的配置变更")
        
        if not recommendations:
            recommendations.append("表现良好，继续保持！")
        
        return recommendations
    
    def get_tool_performance(self) -> Dict[str, Any]:
        """获取工具性能分析"""
        tool_stats = {}
        
        for record in self.learning_records:
            for tc in record.get("tool_calls", []):
                tool_name = tc.get("tool", "unknown")
                
                if tool_name not in tool_stats:
                    tool_stats[tool_name] = {
                        "total_calls": 0,
                        "successful_calls": 0,
                        "failed_calls": 0,
                        "total_time_ms": 0,
                    }
                
                tool_stats[tool_name]["total_calls"] += 1
                
                if record["success"]:
                    tool_stats[tool_name]["successful_calls"] += 1
                else:
                    tool_stats[tool_name]["failed_calls"] += 1
                
                tool_stats[tool_name]["total_time_ms"] += record["execution_time_ms"]
        
        # 计算平均时间
        for tool_name, stats in tool_stats.items():
            if stats["total_calls"] > 0:
                stats["avg_time_ms"] = round(
                    stats["total_time_ms"] / stats["total_calls"], 2
                )
                stats["success_rate"] = round(
                    stats["successful_calls"] / stats["total_calls"] * 100, 2
                )
        
        return tool_stats
    
    def export_learning_report(self) -> str:
        """导出学习报告（Markdown格式）"""
        eval_result = self.evaluate_learning(days=7)
        tool_perf = self.get_tool_performance()
        
        lines = [
            "# Agent学习效果报告",
            f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"\n## 总体表现",
            f"- 评估周期: {eval_result.get('period_days', 0)} 天",
            f"- 总任务数: {eval_result.get('total_tasks', 0)}",
            f"- 成功率: {eval_result.get('success_rate', 0)}%",
            f"- 平均执行时间: {eval_result.get('avg_execution_time_ms', 0)}ms",
        ]
        
        # 趋势
        trends = eval_result.get("improvement_trends", {})
        if trends.get("status") != "insufficient_data":
            lines.extend([
                "\n## 改进趋势",
                f"- 成功率变化: {trends.get('success_rate_change', 0)}%",
                f"- 执行时间变化: {trends.get('execution_time_change_ms', 0)}ms",
                f"- 总体方向: {trends.get('direction', 'unknown')}",
            ])
        
        # 工具性能
        if tool_perf:
            lines.append("\n## 工具性能分析")
            lines.append("\n| 工具 | 调用次数 | 成功率 | 平均时间 |")
            lines.append("|------|---------|--------|----------|")
            
            for tool_name, stats in sorted(
                tool_perf.items(),
                key=lambda x: x[1]["total_calls"],
                reverse=True
            )[:10]:
                lines.append(
                    f"| {tool_name} | {stats['total_calls']} | "
                    f"{stats.get('success_rate', 0)}% | "
                    f"{stats.get('avg_time_ms', 0)}ms |"
                )
        
        # 建议
        recommendations = eval_result.get("recommendations", [])
        if recommendations:
            lines.append("\n## 改进建议")
            for i, rec in enumerate(recommendations, 1):
                lines.append(f"{i}. {rec}")
        
        return "\n".join(lines)
    
    def reset(self):
        """重置学习记录"""
        self.learning_records = []
        self.metrics = {
            "task_success_rate": [],
            "tool_usage_efficiency": [],
            "response_quality": [],
            "error_rate": [],
            "user_satisfaction": [],
        }
        self.improvements = []


# 全局实例
_learning_evaluator = None


def get_learning_evaluator() -> LearningEvaluator:
    """获取全局学习评估器"""
    global _learning_evaluator
    if _learning_evaluator is None:
        _learning_evaluator = LearningEvaluator()
    return _learning_evaluator


def record_task(
    task: str,
    success: bool,
    execution_time_ms: int,
    tool_calls: List[Dict] = None,
    error: str = None,
    user_feedback: str = None,
):
    """便捷函数：记录任务执行"""
    evaluator = get_learning_evaluator()
    evaluator.record_task_execution(
        task=task,
        success=success,
        execution_time_ms=execution_time_ms,
        tool_calls=tool_calls,
        error=error,
        user_feedback=user_feedback,
    )
