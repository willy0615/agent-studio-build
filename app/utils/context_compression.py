"""对话上下文压缩 - 节省Token，保留关键信息"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)


class ContextCompressor:
    """上下文压缩器"""
    
    def __init__(
        self,
        model: str = None,
        max_history_tokens: int = 3000,
        max_summary_tokens: int = 500,
        compression_threshold: int = 10,
    ):
        """
        Args:
            model: 模型名称
            max_history_tokens: 最大历史Token数
            max_summary_tokens: 摘要最大Token数
            compression_threshold: 触发压缩的消息数量阈值
        """
        self.model = model
        self.max_history_tokens = max_history_tokens
        self.max_summary_tokens = max_summary_tokens
        self.compression_threshold = compression_threshold
        
        self.summaries = []
        self.key_facts = {}
        self.user_preferences = {}
    
    def should_compress(self, messages: List[Dict]) -> bool:
        """判断是否需要压缩
        
        Args:
            messages: 消息列表
        
        Returns:
            是否需要压缩
        """
        if len(messages) < self.compression_threshold:
            return False
        
        # 粗略估算Token数
        total_chars = sum(len(m.get("content", "")) for m in messages)
        estimated_tokens = total_chars // 4  # 粗略估计
        
        return estimated_tokens > self.max_history_tokens
    
    def compress(
        self,
        messages: List[Dict],
        keep_recent: int = 3,
    ) -> Dict[str, Any]:
        """压缩对话历史
        
        Args:
            messages: 消息列表
            keep_recent: 保留最近的N条消息
        
        Returns:
            {
                "success": bool,
                "compressed_messages": list,  # 压缩后的消息
                "summary": str,  # 历史摘要
                "key_facts": dict,  # 提取的关键事实
                "compression_ratio": float,  # 压缩率
            }
        """
        if not self.should_compress(messages):
            return {
                "success": True,
                "compressed_messages": messages,
                "summary": "",
                "key_facts": {},
                "compression_ratio": 1.0,
            }
        
        try:
            # 分离旧消息和近期消息
            old_messages = messages[:-keep_recent]
            recent_messages = messages[-keep_recent:]
            
            # 生成摘要
            summary = self._generate_summary(old_messages)
            
            # 提取关键事实
            key_facts = self._extract_key_facts(old_messages)
            
            # 更新内部状态
            self.summaries.append({
                "summary": summary,
                "timestamp": datetime.now().isoformat(),
                "message_count": len(old_messages),
            })
            
            self.key_facts.update(key_facts)
            
            # 构建压缩后的消息
            compressed = self._build_compressed_messages(summary, key_facts, recent_messages)
            
            # 计算压缩率
            original_tokens = sum(len(m.get("content", "")) for m in messages) // 4
            compressed_tokens = sum(len(m.get("content", "")) for m in compressed) // 4
            compression_ratio = compressed_tokens / max(1, original_tokens)
            
            logger.info(f"Context compressed: {len(messages)} -> {len(compressed)} messages, "
                       f"ratio: {compression_ratio:.2f}")
            
            return {
                "success": True,
                "compressed_messages": compressed,
                "summary": summary,
                "key_facts": key_facts,
                "compression_ratio": compression_ratio,
            }
        
        except Exception as e:
            logger.error(f"Compression failed: {e}")
            return {
                "success": False,
                "compressed_messages": messages,
                "error": str(e),
            }
    
    def _generate_summary(self, messages: List[Dict]) -> str:
        """生成对话摘要"""
        try:
            from app.llm_client import chat_completion
            
            # 构建摘要提示
            conversation_text = "\n".join([
                f"{m['role']}: {m['content'][:200]}"
                for m in messages[-20:]  # 最多20条
            ])
            
            prompt = f"""请总结以下对话的关键内容，保留重要信息：

{conversation_text}

要求：
1. 突出关键决策和结论
2. 保留用户偏好和需求
3. 记录重要的上下文信息
4. 控制在200字以内

摘要："""
            
            response = chat_completion(
                [{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.3,
            )
            
            summary = response.get("content", "")
            
            # 截断过长的摘要
            if len(summary) > 500:
                summary = summary[:500] + "..."
            
            return summary
        
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            # 降级：简单拼接
            return self._simple_summary(messages)
    
    def _simple_summary(self, messages: List[Dict]) -> str:
        """简单摘要（降级方案）"""
        user_messages = [m for m in messages if m.get("role") == "user"]
        assistant_messages = [m for m in messages if m.get("role") == "assistant"]
        
        summary_parts = [
            f"对话包含 {len(user_messages)} 个用户问题和 {len(assistant_messages)} 个回答。",
        ]
        
        # 提取前几个主题
        topics = []
        for m in user_messages[:5]:
            content = m.get("content", "")
            # 提取前30个字符作为主题
            if content:
                topics.append(content[:30])
        
        if topics:
            summary_parts.append(f"主要话题: {', '.join(topics)}")
        
        return " ".join(summary_parts)
    
    def _extract_key_facts(self, messages: List[Dict]) -> Dict[str, Any]:
        """提取关键事实"""
        facts = {}
        
        try:
            from app.llm_client import chat_completion
            
            # 构建提取提示
            conversation_text = "\n".join([
                f"{m['role']}: {m['content'][:150]}"
                for m in messages[-15:]
            ])
            
            prompt = f"""从以下对话中提取关键事实，以JSON格式输出：

{conversation_text}

输出格式：
{{
  "user_name": "用户姓名（如果提到）",
  "user_goal": "用户目标",
  "preferences": ["偏好列表"],
  "constraints": ["限制条件"],
  "context": ["重要上下文"],
  "decisions": ["已做出的决定"]
}}

JSON："""
            
            response = chat_completion(
                [{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.2,
            )
            
            # 解析JSON
            import re
            json_match = re.search(r'{[\s\S]+}', response.get("content", ""))
            
            if json_match:
                facts = json.loads(json_match.group(0))
        
        except Exception as e:
            logger.warning(f"Key fact extraction failed: {e}")
        
        return facts
    
    def _build_compressed_messages(
        self,
        summary: str,
        key_facts: Dict,
        recent_messages: List[Dict],
    ) -> List[Dict]:
        """构建压缩后的消息列表"""
        compressed = []
        
        # 1. 添加摘要消息
        if summary:
            compressed.append({
                "role": "system",
                "content": f"[对话历史摘要]\n{summary}",
            })
        
        # 2. 添加关键事实
        if key_facts:
            facts_text = []
            
            if key_facts.get("user_goal"):
                facts_text.append(f"用户目标: {key_facts['user_goal']}")
            
            if key_facts.get("preferences"):
                facts_text.append(f"用户偏好: {', '.join(key_facts['preferences'][:5])}")
            
            if key_facts.get("constraints"):
                facts_text.append(f"限制条件: {', '.join(key_facts['constraints'][:5])}")
            
            if key_facts.get("decisions"):
                facts_text.append(f"已做决定: {', '.join(key_facts['decisions'][:5])}")
            
            if facts_text:
                compressed.append({
                    "role": "system",
                    "content": "[关键事实]\n" + "\n".join(facts_text),
                })
        
        # 3. 添加近期消息
        compressed.extend(recent_messages)
        
        return compressed
    
    def get_compression_stats(self) -> Dict[str, Any]:
        """获取压缩统计"""
        return {
            "total_summaries": len(self.summaries),
            "key_facts_count": len(self.key_facts),
            "user_preferences_count": len(self.user_preferences),
            "last_compression": self.summaries[-1] if self.summaries else None,
        }
    
    def reset(self):
        """重置压缩器状态"""
        self.summaries = []
        self.key_facts = {}
        self.user_preferences = {}


# 全局实例
_compressor = None


def get_compressor(model: str = None) -> ContextCompressor:
    """获取全局压缩器实例"""
    global _compressor
    if _compressor is None:
        _compressor = ContextCompressor(model=model)
    return _compressor


def compress_context(
    messages: List[Dict],
    model: str = None,
    keep_recent: int = 3,
) -> Dict[str, Any]:
    """便捷函数：压缩上下文
    
    Args:
        messages: 消息列表
        model: 模型名称
        keep_recent: 保留最近N条消息
    
    Returns:
        压缩结果
    """
    compressor = get_compressor(model)
    return compressor.compress(messages, keep_recent)
