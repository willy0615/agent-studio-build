"""性能监控 - 实时追踪系统性能"""
import time
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
import threading
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime, timedelta
from pathlib import Path
import json
import logging
from functools import wraps
from collections import defaultdict

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, storage_dir: str = None):
        """
        Args:
            storage_dir: 监控数据存储目录
        """
        self.storage_dir = Path(storage_dir or "E:/AgentProject/data/monitoring")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.metrics = {
            "api_calls": 0,
            "total_latency_ms": 0,
            "errors": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "tool_calls": defaultdict(int),
            "model_calls": defaultdict(int),
        }
        
        self.latency_history = []
        self.error_history = []
        self.max_history = 1000
        
        self._lock = threading.Lock()
        self._start_time = time.time()
        
        self._load_metrics()
    
    def _load_metrics(self):
        """加载历史指标"""
        metrics_file = self.storage_dir / "performance_metrics.json"
        if metrics_file.exists():
            try:
                with open(metrics_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.metrics["api_calls"] = data.get("api_calls", 0)
                    self.metrics["total_latency_ms"] = data.get("total_latency_ms", 0)
                    self.metrics["errors"] = data.get("errors", 0)
            except Exception as e:
                logger.warning(f"Failed to load metrics: {e}")
    
    def _save_metrics(self):
        """保存指标"""
        metrics_file = self.storage_dir / "performance_metrics.json"
        try:
            with open(metrics_file, "w", encoding="utf-8") as f:
                json.dump({
                    "api_calls": self.metrics["api_calls"],
                    "total_latency_ms": self.metrics["total_latency_ms"],
                    "errors": self.metrics["errors"],
                    "last_updated": datetime.now().isoformat(),
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
    
    def profile(self, func_name: str = None):
        """
        性能分析装饰器
        
        Args:
            func_name: 函数名称（可选）
        
        Returns:
            装饰器
        """
        def decorator(func: Callable):
            name = func_name or func.__name__
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    
                    # 记录成功
                    with self._lock:
                        latency_ms = int((time.time() - start_time) * 1000)
                        self.metrics["api_calls"] += 1
                        self.metrics["total_latency_ms"] += latency_ms
                        
                        self.latency_history.append({
                            "function": name,
                            "latency_ms": latency_ms,
                            "timestamp": datetime.now().isoformat(),
                            "success": True,
                        })
                        
                        if len(self.latency_history) > self.max_history:
                            self.latency_history = self.latency_history[-self.max_history:]
                    
                    return result
                
                except Exception as e:
                    # 记录错误
                    with self._lock:
                        self.metrics["errors"] += 1
                        
                        self.error_history.append({
                            "function": name,
                            "error": str(e),
                            "timestamp": datetime.now().isoformat(),
                        })
                        
                        if len(self.error_history) > self.max_history:
                            self.error_history = self.error_history[-self.max_history:]
                    
                    raise
                
                finally:
                    self._save_metrics()
            
            return wrapper
        return decorator
    
    def record_tool_call(self, tool_name: str, latency_ms: int = 0, success: bool = True):
        """记录工具调用"""
        with self._lock:
            self.metrics["tool_calls"][tool_name] += 1
            
            if latency_ms > 0:
                self.latency_history.append({
                    "function": f"tool:{tool_name}",
                    "latency_ms": latency_ms,
                    "timestamp": datetime.now().isoformat(),
                    "success": success,
                })
    
    def record_model_call(self, model: str, latency_ms: int = 0, tokens: int = 0):
        """记录模型调用"""
        with self._lock:
            self.metrics["model_calls"][model] += 1
            
            if latency_ms > 0:
                self.latency_history.append({
                    "function": f"model:{model}",
                    "latency_ms": latency_ms,
                    "tokens": tokens,
                    "timestamp": datetime.now().isoformat(),
                    "success": True,
                })
    
    def record_cache_hit(self):
        """记录缓存命中"""
        with self._lock:
            self.metrics["cache_hits"] += 1
    
    def record_cache_miss(self):
        """记录缓存未命中"""
        with self._lock:
            self.metrics["cache_misses"] += 1
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """获取系统资源指标"""
        if not HAS_PSUTIL:
            return {
                "cpu_percent": 0,
                "memory_percent": 0,
                "memory_used_gb": 0,
                "memory_total_gb": 0,
                "disk_percent": 0,
                "disk_used_gb": 0,
                "disk_total_gb": 0,
                "uptime_seconds": int(time.time() - self._start_time),
                "note": "psutil not installed",
            }
        
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_gb": round(memory.used / (1024 ** 3), 2),
                "memory_total_gb": round(memory.total / (1024 ** 3), 2),
                "disk_percent": disk.percent,
                "disk_used_gb": round(disk.used / (1024 ** 3), 2),
                "disk_total_gb": round(disk.total / (1024 ** 3), 2),
                "uptime_seconds": int(time.time() - self._start_time),
            }
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {}
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        with self._lock:
            total_requests = self.metrics["api_calls"]
            avg_latency = (
                self.metrics["total_latency_ms"] / max(1, total_requests)
            )
            
            total_cache = self.metrics["cache_hits"] + self.metrics["cache_misses"]
            cache_hit_rate = (
                self.metrics["cache_hits"] / max(1, total_cache) * 100
            )
            
            error_rate = (
                self.metrics["errors"] / max(1, total_requests) * 100
            )
            
            return {
                "total_requests": total_requests,
                "total_errors": self.metrics["errors"],
                "error_rate": f"{error_rate:.1f}%",
                "avg_latency_ms": int(avg_latency),
                "cache_hit_rate": f"{cache_hit_rate:.1f}%",
                "total_tool_calls": sum(self.metrics["tool_calls"].values()),
                "total_model_calls": sum(self.metrics["model_calls"].values()),
            }
    
    def get_latency_trend(self, minutes: int = 60) -> List[Dict]:
        """获取延迟趋势"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        
        with self._lock:
            return [
                entry for entry in self.latency_history
                if datetime.fromisoformat(entry["timestamp"]) >= cutoff
            ]
    
    def get_top_slow_functions(self, limit: int = 10) -> List[Dict]:
        """获取最慢的函数"""
        with self._lock:
            # 按函数分组计算平均延迟
            func_latencies = defaultdict(list)
            
            for entry in self.latency_history:
                func_latencies[entry["function"]].append(entry["latency_ms"])
            
            # 计算平均值并排序
            avg_latencies = [
                {
                    "function": func,
                    "avg_latency_ms": sum(latencies) / len(latencies),
                    "call_count": len(latencies),
                }
                for func, latencies in func_latencies.items()
            ]
            
            # 按平均延迟排序
            avg_latencies.sort(key=lambda x: x["avg_latency_ms"], reverse=True)
            
            return avg_latencies[:limit]
    
    def get_tool_usage_stats(self) -> Dict[str, int]:
        """获取工具使用统计"""
        with self._lock:
            return dict(self.metrics["tool_calls"])
    
    def get_model_usage_stats(self) -> Dict[str, int]:
        """获取模型使用统计"""
        with self._lock:
            return dict(self.metrics["model_calls"])
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict]:
        """获取最近的错误"""
        with self._lock:
            return self.error_history[-limit:]
    
    def reset(self):
        """重置所有指标"""
        with self._lock:
            self.metrics = {
                "api_calls": 0,
                "total_latency_ms": 0,
                "errors": 0,
                "cache_hits": 0,
                "cache_misses": 0,
                "tool_calls": defaultdict(int),
                "model_calls": defaultdict(int),
            }
            self.latency_history = []
            self.error_history = []
        
        self._save_metrics()
        logger.info("Performance metrics reset")
    
    def export_report(self) -> str:
        """导出性能报告"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "performance_summary": self.get_performance_summary(),
            "system_metrics": self.get_system_metrics(),
            "tool_usage": self.get_tool_usage_stats(),
            "model_usage": self.get_model_usage_stats(),
            "top_slow_functions": self.get_top_slow_functions(),
            "recent_errors": self.get_recent_errors(limit=20),
        }
        
        output_path = self.storage_dir / f"performance_report_{datetime.now():%Y%m%d_%H%M%S}.json"
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Performance report exported: {output_path}")
        return str(output_path)


# 全局监控器实例
_monitor = None


def get_monitor() -> PerformanceMonitor:
    """获取全局监控器实例"""
    global _monitor
    if _monitor is None:
        _monitor = PerformanceMonitor()
    return _monitor


# 便捷装饰器
def profile_performance(func_name: str = None):
    """性能分析装饰器"""
    return get_monitor().profile(func_name)
