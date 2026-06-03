"""线程安全的统计模块"""
from dataclasses import dataclass, field
from typing import Dict
from datetime import datetime
import json
import threading
from pathlib import Path
from app.config import DATA_DIR


class Stats:
    """Track usage statistics for the agent session (thread-safe)."""
    
    def __init__(self):
        self._lock = threading.Lock()
        # API调用统计
        self.api_calls: int = 0
        self.total_tokens_estimate: int = 0
        self.total_time_ms: int = 0
        # Agent调用统计
        self.agent_calls: Dict[str, int] = {}
        # 模型调用统计
        self.model_calls: Dict[str, int] = {}
        # 会话信息
        self.session_start: str = datetime.now().isoformat()
        self.message_count: int = 0
    
    def record_api_call(self, model: str, tokens_estimate: int, time_ms: int):
        with self._lock:
            self.api_calls += 1
            self.total_tokens_estimate += tokens_estimate
            self.total_time_ms += time_ms
            self.model_calls[model] = self.model_calls.get(model, 0) + 1
    
    def record_agent_call(self, agent: str):
        with self._lock:
            self.agent_calls[agent] = self.agent_calls.get(agent, 0) + 1
    
    def record_model_call(self, model: str):
        with self._lock:
            self.model_calls[model] = self.model_calls.get(model, 0) + 1
    
    def record_message(self):
        with self._lock:
            self.message_count += 1
    
    def to_dict(self) -> dict:
        with self._lock:
            return {
                "api_calls": self.api_calls,
                "total_tokens_estimate": self.total_tokens_estimate,
                "total_time_ms": self.total_time_ms,
                "avg_time_ms": self.total_time_ms // max(1, self.api_calls),
                "agent_calls": dict(self.agent_calls),
                "model_calls": dict(self.model_calls),
                "session_start": self.session_start,
                "message_count": self.message_count,
            }
    
    def reset(self):
        with self._lock:
            self.api_calls = 0
            self.total_tokens_estimate = 0
            self.total_time_ms = 0
            self.agent_calls = {}
            self.model_calls = {}
            self.session_start = datetime.now().isoformat()
            self.message_count = 0
    
    def save(self, filepath: Path = None):
        """Save stats to file."""
        if filepath is None:
            filepath = DATA_DIR / "stats.json"
        data = self.to_dict()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load(self, filepath: Path = None):
        """Load stats from file."""
        if filepath is None:
            filepath = DATA_DIR / "stats.json"
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            with self._lock:
                self.api_calls = data.get("api_calls", 0)
                self.total_tokens_estimate = data.get("total_tokens_estimate", 0)
                self.total_time_ms = data.get("total_time_ms", 0)
                self.agent_calls = data.get("agent_calls", {})
                self.model_calls = data.get("model_calls", {})
                self.session_start = data.get("session_start", datetime.now().isoformat())
                self.message_count = data.get("message_count", 0)


# 全局统计实例
_global_stats: Stats = None
_stats_lock = threading.Lock()


def get_stats() -> Stats:
    """Get or create global stats instance (thread-safe)."""
    global _global_stats
    if _global_stats is None:
        with _stats_lock:
            if _global_stats is None:
                _global_stats = Stats()
                _global_stats.load()
    return _global_stats


def reset_stats():
    """Reset global statistics."""
    get_stats().reset()
