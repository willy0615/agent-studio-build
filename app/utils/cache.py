"""LLM缓存机制 - 降低API成本，提升响应速度"""
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class LLMCache:
    """LLM响应缓存系统"""
    
    def __init__(self, cache_dir: str = None, ttl_hours: int = 24):
        """
        Args:
            cache_dir: 缓存目录
            ttl_hours: 缓存有效期（小时）
        """
        self.cache_dir = Path(cache_dir or "E:/AgentProject/data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "llm_cache.json"
        self.ttl_hours = ttl_hours
        self.cache = {}
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
        }
        self._load()
    
    def _load(self):
        """加载缓存"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.cache = data.get("cache", {})
                    self.stats = data.get("stats", self.stats)
                
                # 清理过期缓存
                self._evict_expired()
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
                self.cache = {}
    
    def _save(self):
        """保存缓存"""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump({
                    "cache": self.cache,
                    "stats": self.stats,
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def _evict_expired(self):
        """清理过期缓存"""
        now = datetime.now()
        expired_keys = []
        
        for key, entry in self.cache.items():
            cached_time = datetime.fromisoformat(entry.get("timestamp", "2000-01-01"))
            if now - cached_time > timedelta(hours=self.ttl_hours):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
            self.stats["evictions"] += 1
        
        if expired_keys:
            self._save()
            logger.info(f"Evicted {len(expired_keys)} expired cache entries")
    
    def _generate_key(self, messages: list, model: str, **kwargs) -> str:
        """生成缓存键"""
        # 将消息和参数序列化
        cache_data = {
            "messages": messages,
            "model": model,
            "kwargs": kwargs,
        }
        data_str = json.dumps(cache_data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def get(self, messages: list, model: str, **kwargs) -> Optional[str]:
        """获取缓存响应"""
        key = self._generate_key(messages, model, **kwargs)
        
        if key in self.cache:
            entry = self.cache[key]
            
            # 检查是否过期
            cached_time = datetime.fromisoformat(entry.get("timestamp"))
            if datetime.now() - cached_time > timedelta(hours=self.ttl_hours):
                del self.cache[key]
                self.stats["misses"] += 1
                return None
            
            # 缓存命中
            self.stats["hits"] += 1
            logger.info(f"Cache hit for model {model}")
            return entry.get("response")
        
        self.stats["misses"] += 1
        return None
    
    def set(self, messages: list, model: str, response: str, **kwargs):
        """设置缓存"""
        key = self._generate_key(messages, model, **kwargs)
        
        self.cache[key] = {
            "response": response,
            "model": model,
            "timestamp": datetime.now().isoformat(),
            "message_count": len(messages),
        }
        
        self._save()
        logger.info(f"Cached response for model {model}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / max(1, total_requests) * 100
        
        return {
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "evictions": self.stats["evictions"],
            "hit_rate": f"{hit_rate:.1f}%",
            "cache_size": len(self.cache),
        }
    
    def clear(self):
        """清空缓存"""
        self.cache = {}
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
        }
        self._save()
        logger.info("Cache cleared")


class SemanticCache:
    """语义缓存 - 基于相似度匹配（可选）"""
    
    def __init__(self, similarity_threshold: float = 0.95):
        """
        Args:
            similarity_threshold: 相似度阈值（0-1）
        """
        self.threshold = similarity_threshold
        self.embeddings = {}  # 存储查询的嵌入
        self.responses = {}   # 存储对应的响应
    
    def get_similar(self, query: str, embed_func) -> Optional[str]:
        """查找相似查询的响应"""
        # 如果没有嵌入函数，跳过
        if not embed_func:
            return None
        
        try:
            query_embedding = embed_func(query)
            
            for cached_query, cached_embedding in self.embeddings.items():
                similarity = self._cosine_similarity(query_embedding, cached_embedding)
                
                if similarity >= self.threshold:
                    logger.info(f"Semantic cache hit (similarity: {similarity:.2f})")
                    return self.responses.get(cached_query)
            
            return None
        except Exception as e:
            logger.warning(f"Semantic cache error: {e}")
            return None
    
    @staticmethod
    def _cosine_similarity(a: list, b: list) -> float:
        """计算余弦相似度"""
        import numpy as np
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


# 全局缓存实例
_cache_instance = None


def get_cache() -> LLMCache:
    """获取全局缓存实例"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = LLMCache()
    return _cache_instance
