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
        LongTermMemory().save(self.session_id, key_info, important=True)


class LongTermMemory:
    """Persists important memories to local JSON files."""

    def __init__(self):
        self.memory_file = MEMORY_DIR / "long_term.json"
        self.profile_file = MEMORY_DIR / "user_profile.json"
        self.memories = {}
        self.profile = {}
        self._load()
        self._load_profile()
    
    def _load(self):
        """Load memories from file."""
        if self.memory_file.exists():
            with open(self.memory_file, "r", encoding="utf-8") as f:
                self.memories = json.load(f)
        else:
            self.memories = {}
    
    def _load_profile(self):
        """Load user profile."""
        if self.profile_file.exists():
            with open(self.profile_file, "r", encoding="utf-8") as f:
                self.profile = json.load(f)
        else:
            self.profile = {
                "preferences": {},
                "interests": [],
                "frequently_used_tools": {},
                "preferred_model": None,
                "language": "auto",
                "conversation_count": 0,
            }

    def save(self, session_id: str, info: str, important: bool = False):
        """Save memory. Only saves if important=True or manually triggered."""
        if not important and not info.startswith("USER_SAVE:"):
            return
        
        timestamp = datetime.now().isoformat()
        if session_id not in self.memories:
            self.memories[session_id] = []
        
        self.memories[session_id].append({
            "timestamp": timestamp,
            "content": info,
        })
        self._flush()
    
    def update_preference(self, key: str, value: str):
        """Update user preference."""
        self.profile["preferences"][key] = value
        self._flush_profile()
    
    
    def record_tool_usage(self, tool_name: str):
        """Record tool usage for analytics."""
        if tool_name not in self.profile["frequently_used_tools"]:
            self.profile["frequently_used_tools"][tool_name] = 0
        self.profile["frequently_used_tools"][tool_name] += 1
        self._flush_profile()
    
    
    def record_interest(self, topic: str):
        """Record user interest topic."""
        if topic not in self.profile["interests"]:
            self.profile["interests"].append(topic)
            self._flush_profile()
    
    
    def get_profile_context(self) -> str:
        """Get user profile as context for LLM."""
        parts = []
        
        if self.profile["preferences"]:
            prefs = ", ".join([f"{k}: {v}" for k, v in self.profile["preferences"].items()])
            parts.append(f"User preferences: {prefs}")
        
        if self.profile["interests"]:
            parts.append(f"User interests: {', '.join(self.profile['interests'][:5])}")
        
        
        if self.profile["frequently_used_tools"]:
            top_tools = sorted(
                self.profile["frequently_used_tools"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            parts.append(f"Frequently used tools: {', '.join([t[0] for t in top_tools])}")
        
        
        return "\n".join(parts) if parts else ""
    
    
    def _flush_profile(self):
        with open(self.profile_file, "w", encoding="utf-8") as f:
            json.dump(self.profile, f, ensure_ascii=False, indent=2)

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
