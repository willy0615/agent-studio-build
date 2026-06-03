"""Agent思考过程可视化 - 实时显示推理过程"""
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


class AgentThoughtStream:
    """Agent思考流 - 实时记录和展示"""
    
    def __init__(self):
        self.thoughts = []
        self.current_session = None
        self.callbacks = []
    
    def start_session(self, task: str, mode: str = "react"):
        """开始新会话"""
        self.current_session = {
            "session_id": f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "task": task,
            "mode": mode,
            "start_time": datetime.now().isoformat(),
            "steps": [],
            "status": "running",
        }
        
        self._notify_callbacks("session_start", self.current_session)
        return self.current_session["session_id"]
    
    def end_session(self, result: Dict[str, Any]):
        """结束会话"""
        if self.current_session:
            self.current_session["end_time"] = datetime.now().isoformat()
            self.current_session["status"] = "completed" if result.get("success") else "failed"
            self.current_session["result"] = result
            
            self.thoughts.append(self.current_session)
            self._notify_callbacks("session_end", self.current_session)
    
    def add_thought(
        self,
        step_type: str,
        content: str,
        details: Dict = None,
    ):
        """添加思考步骤
        
        Args:
            step_type: 类型
                - "thinking": 思考
                - "tool_call": 工具调用
                - "tool_result": 工具结果
                - "reasoning": 推理
                - "decision": 决策
                - "error": 错误
            content: 内容
            details: 详细信息
        """
        if not self.current_session:
            return
        
        step = {
            "step": len(self.current_session["steps"]) + 1,
            "type": step_type,
            "content": content,
            "details": details or {},
            "timestamp": datetime.now().isoformat(),
        }
        
        self.current_session["steps"].append(step)
        self._notify_callbacks("thought", step)
        
        return step
    
    def add_callback(self, callback: Callable):
        """添加回调函数
        
        Args:
            callback: 回调函数，接收(event_type, data)
        """
        self.callbacks.append(callback)
    
    def _notify_callbacks(self, event_type: str, data: Any):
        """通知所有回调"""
        for callback in self.callbacks:
            try:
                callback(event_type, data)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def get_current_session(self) -> Optional[Dict]:
        """获取当前会话"""
        return self.current_session
    
    def get_session_history(self, limit: int = 10) -> List[Dict]:
        """获取历史会话"""
        return self.thoughts[-limit:]
    
    def format_for_display(self, session: Dict = None) -> str:
        """格式化为显示文本
        
        Args:
            session: 会话数据，None则使用当前会话
        
        Returns:
            格式化的文本
        """
        session = session or self.current_session
        if not session:
            return ""
        
        lines = []
        
        # 标题
        lines.append(f"## 🤖 Agent执行过程")
        lines.append(f"**任务**: {session['task']}")
        lines.append(f"**模式**: {session['mode']}")
        lines.append(f"**状态**: {session['status']}")
        lines.append("")
        
        # 步骤
        for step in session["steps"]:
            step_type = step["type"]
            content = step["content"]
            timestamp = step["timestamp"].split("T")[1][:8]
            
            # 图标映射
            icons = {
                "thinking": "🤔",
                "tool_call": "🔧",
                "tool_result": "📊",
                "reasoning": "🧠",
                "decision": "✅",
                "error": "❌",
            }
            
            icon = icons.get(step_type, "•")
            
            lines.append(f"### {icon} Step {step['step']}: {step_type}")
            lines.append(f"`{timestamp}` {content}")
            
            # 详细信息
            if step["details"]:
                details_str = json.dumps(step["details"], ensure_ascii=False, indent=2)
                lines.append(f"```json\n{details_str}\n```")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def export_session(self, session_id: str = None) -> Dict[str, Any]:
        """导出会话数据"""
        if session_id:
            for session in self.thoughts:
                if session["session_id"] == session_id:
                    return session
            return None
        else:
            return self.current_session


class StreamlitThoughtVisualizer:
    """Streamlit思考可视化组件"""
    
    def __init__(self, thought_stream: AgentThoughtStream):
        self.thought_stream = thought_stream
        self.container = None
        self.placeholder = None
    
    def start(self, container=None):
        """启动可视化"""
        try:
            import streamlit as st
            
            self.container = container or st.container()
            
            # 创建回调
            def update_display(event_type: str, data: Any):
                self._render(event_type, data)
            
            self.thought_stream.add_callback(update_display)
            
            logger.info("Thought visualizer started")
        
        except ImportError:
            logger.warning("Streamlit not available, visualization disabled")
    
    def _render(self, event_type: str, data: Any):
        """渲染更新"""
        if not self.container:
            return
        
        try:
            import streamlit as st
            
            with self.container:
                if event_type == "session_start":
                    st.markdown(f"### 🤖 Agent开始执行")
                    st.markdown(f"**任务**: {data['task']}")
                    st.markdown(f"**模式**: {data['mode']}")
                    self.placeholder = st.empty()
                
                elif event_type == "thought":
                    step = data
                    step_type = step["type"]
                    
                    # 渲染步骤
                    icons = {
                        "thinking": "🤔",
                        "tool_call": "🔧",
                        "tool_result": "📊",
                        "reasoning": "🧠",
                        "decision": "✅",
                        "error": "❌",
                    }
                    
                    icon = icons.get(step_type, "•")
                    
                    if step_type == "thinking":
                        st.info(f"{icon} **思考**: {step['content']}")
                    
                    elif step_type == "tool_call":
                        tool_name = step["details"].get("tool", "unknown")
                        st.code(f"{icon} 调用工具: {tool_name}", language="text")
                        with st.expander("参数"):
                            st.json(step["details"].get("parameters", {}))
                    
                    elif step_type == "tool_result":
                        st.success(f"{icon} 工具返回")
                        if step["details"]:
                            st.text(str(step["details"].get("result", ""))[:200])
                    
                    elif step_type == "reasoning":
                        st.info(f"{icon} **推理**: {step['content']}")
                    
                    elif step_type == "decision":
                        st.success(f"{icon} **决策**: {step['content']}")
                    
                    elif step_type == "error":
                        st.error(f"{icon} **错误**: {step['content']}")
                
                elif event_type == "session_end":
                    status = "✅ 完成" if data["status"] == "completed" else "❌ 失败"
                    st.markdown(f"### {status}")
        
        except Exception as e:
            logger.error(f"Render error: {e}")


# 思考流装饰器
def track_thoughts(func):
    """装饰器：自动跟踪函数的思考过程"""
    def wrapper(*args, **kwargs):
        stream = get_thought_stream()
        
        # 记录开始
        func_name = func.__name__
        stream.add_thought("thinking", f"开始执行: {func_name}")
        
        try:
            # 执行函数
            result = func(*args, **kwargs)
            
            # 记录成功
            stream.add_thought("decision", f"执行完成: {func_name}")
            
            return result
        
        except Exception as e:
            # 记录错误
            stream.add_thought("error", f"执行失败: {str(e)}")
            raise
    
    return wrapper


# 全局实例
_thought_stream = None


def get_thought_stream() -> AgentThoughtStream:
    """获取全局思考流"""
    global _thought_stream
    if _thought_stream is None:
        _thought_stream = AgentThoughtStream()
    return _thought_stream
