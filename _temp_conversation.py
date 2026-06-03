import json
from datetime import datetime
from pathlib import Path
from app.config import MEMORY_DIR
from typing import List, Dict


class ConversationMemory:
    """Manages multi-turn conversation history with summarization."""

    def __init__(self, session_id: str = "default"):
        self.session_id = session_id
        self.messages: List[Dict[str, str]] = []
        self.max_turns = 50
        self.summary = ""  # 压缩摘要

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})
        # 接近上限时压缩
        if len(self.messages) > self.max_turns * 1.5:
            self._compress_old_messages()

    def get_messages(self) -> list:
        """Return messages in OpenAI chat format."""
        return self.messages.copy()

    def get_context_window(self, max_messages: int = 20) -> list:
        """Return recent messages + summary for context."""
        recent = self.messages[-max_messages:]
        if self.summary:
            # 在开头注入摘要
            return [
                {"role": "system", "content": f"[Earlier conversation summary]\n{self.summary}"}
            ] + recent
        return recent

    def _compress_old_messages(self):
        """Compress old messages into a summary."""
        if len(self.messages) <= self.max_turns:
            return
        
        old_messages = self.messages[:-self.max_turns]
        self.messages = self.messages[-self.max_turns:]
        
        # 简单压缩：提取关键信息（后续可用LLM增强）
        key_info = []
        for msg in old_messages[::2]:  # 每隔一条取
            content = msg["content"][:200]
            role = msg["role"]
            key_info.append(f"{role}: {content}")
        
        if key_info:
            self.summary = "\n".join(key_info[-10:])  # 保留最近10条关键信息

    def clear(self):
        self.messages = []
        self.summary = ""

    def save_to_long_term(self, key_info: str):
        """Save important info to long-term memory."""
        LongTermMemory().save(self.session_id, key_info)


class LongTermMemory:
    """Persists important memories to local JSON files."""

    def __init__(self):
        self.memory_file = MEMORY_DIR / "long_term.json"
        self._load()

    def _load(self):
        if self.memory_file.exists():
            with open(self.memory_file, "r", encoding="utf-8") as f:
                self.memories = json.load(f)
        else:
            self.memories = {}

    def save(self, session_id: str, info: str, important: bool = False):
        """Save memory. Only saves if important=True or manually triggered.
        
        Args:
            session_id: Session identifier
            info: Memory content
            important: If True, always save; if False, skip by default
        """
        if not important and not info.startswith("USER_SAVE:"):
            return  # 自动保存只保存重要信息
        
        timestamp = datetime.now().isoformat()
        if session_id not in self.memories:
            self.memories[session_id] = []
        
        self.memories[session_id].append({
            "timestamp": timestamp,
            "content": info,
        })
        self._flush()

    def _flush(self):
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(self.memories, f, ensure_ascii=False, indent=2)

    def get_all(self, session_id: str = None) -> list:
        if session_id:
            return self.memories.get(session_id, [])
        all_memories = []
        for session_mems in self.memories.values():
            all_memories.extend(session_mems)
        return all_memories

    def search(self, keyword: str, limit: int = 5) -> list:
        """Simple keyword search in memories."""
        results = []
        keyword = keyword.lower()
        for session_id, mems in self.memories.items():
            for mem in mems:
                if keyword in mem["content"].lower():
                    results.append(mem)
                    if len(results) >= limit:
                        return results
        return results

    def clear(self, session_id: str = None):
        if session_id:
            self.memories.pop(session_id, None)
        else:
            self.memories = {}
        self._flush()
