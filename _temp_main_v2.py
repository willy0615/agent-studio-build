import streamlit as st
import sys
from pathlib import Path
from datetime import datetime
import json

sys.path.insert(0, str(Path(__file__).parent))

from app.config import AVAILABLE_MODELS, DEFAULT_MODEL, KNOWLEDGE_BASE_DIR
from app.memory.conversation import ConversationMemory, LongTermMemory
from app.agents.autonomous import run_agent
from app.rag.vectorstore import add_documents, list_collections, delete_collection
from app.tools.document_parser import parse_file
from app.utils.stats import get_stats, reset_stats


def main():
    st.set_page_config(page_title="Autonomous Agent", page_icon="🤖", layout="wide")

    # Session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "memory" not in st.session_state:
        st.session_state.memory = ConversationMemory()
    if "current_model" not in st.session_state:
        st.session_state.current_model = DEFAULT_MODEL
    if "execution_mode" not in st.session_state:
        st.session_state.execution_mode = "auto"
    if "last_metadata" not in st.session_state:
        st.session_state.last_metadata = {}
    if "stats" not in st.session_state:
        st.session_state.stats = get_stats()

    # --- Sidebar ---
    with st.sidebar:
        st.header("⚙️ Configuration")

        # 模型选择
        model_label = st.selectbox(
            "Model",
            list(AVAILABLE_MODELS.keys()),
            index=list(AVAILABLE_MODELS.keys()).index("DeepSeek V4 Flash"),
        )
        st.session_state.current_model = AVAILABLE_MODELS[model_label]

        # 执行模式选择
        st.subheader("🧠 Execution Mode")
        mode = st.radio(
            "Mode",
            ["auto", "simple", "react"],
            format_func=lambda x: {
                "auto": "⚡ Auto (智能选择)",
                "simple": "💬 Simple (单轮问答)",
                "react": "🔄 ReAct (推理+行动)",
            }[x],
        )
        st.session_state.execution_mode = mode
        
        st.caption("""
**模式说明:**
- **Auto**: 自动判断任务复杂度
- **Simple**: 快速问答，无工具循环
- **ReAct**: 多步骤推理+工具调用
        """)

        st.divider()

        # 使用统计
        st.subheader("📊 Usage Stats")
        stats = st.session_state.stats
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Tasks", stats.message_count)
            st.metric("Tool Calls", sum(stats.agent_calls.values()))
        with col2:
            st.metric("Est. Tokens", f"{stats.total_tokens_estimate:,}")
            st.metric("Avg Time", f"{stats.total_time_ms // max(1, stats.message_count)}ms")
        
        if st.button("Reset Stats"):
            reset_stats()
            st.session_state.stats = get_stats()
            st.rerun()

        st.divider()

        # Knowledge Base
        st.subheader("📚 Knowledge Base")
        kb_collections = list_collections()
        st.write(f"Collections: {len(kb_collections)}")
        for col_name in kb_collections[:5]:
            st.write(f"• {col_name}")

        uploaded_files = st.file_uploader(
            "Add Documents",
            type=["txt", "md", "html", "py", "pdf"],
            accept_multiple_files=True,
        )
        if uploaded_files and st.button("Upload"):
            for f in uploaded_files:
                content = f.read().decode("utf-8", errors="ignore")
                add_documents("knowledge_base", [content], metadatas=[{"filename": f.name}])
            st.success(f"Added {len(uploaded_files)} documents")
            st.rerun()

        st.divider()

        # Memory
        if st.button("🗑️ Clear Conversation"):
            st.session_state.messages = []
            st.session_state.memory.clear()
            st.rerun()

    # --- Main Area ---
    st.title("🤖 Autonomous Agent")
    st.caption("全能智能体 | 自主规划 · 多工具协同 · ReAct推理 | Powered by NVIDIA NIM")

    # 显示对话历史
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
            # 显示工具调用详情
            if msg.get("tool_calls"):
                with st.expander(f"🔧 Tool Calls ({len(msg['tool_calls'])})", expanded=False):
                    for tc in msg["tool_calls"]:
                        st.json({
                            "tool": tc.get("tool"),
                            "parameters": tc.get("parameters"),
                            "success": tc.get("result", {}).get("success"),
                        })

    # 用户输入
    if prompt := st.chat_input("Give me a task..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.memory.add_message("user", prompt)
        st.session_state.stats.record_message()
        
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            # 显示执行状态
            status = st.empty()
            status.info(f"🚀 Executing in **{st.session_state.execution_mode}** mode...")
            
            # 执行任务
            history = st.session_state.memory.get_context_window()
            result = run_agent(
                task=prompt,
                model=st.session_state.current_model,
                mode=st.session_state.execution_mode,
                history=history,
            )
            
            status.empty()
            
            # 显示结果
            st.markdown(result["answer"])
            
            # 元数据
            meta_col1, meta_col2, meta_col3 = st.columns(3)
            with meta_col1:
                st.caption(f"🎯 Mode: **{result.get('mode', 'unknown')}**")
            with meta_col2:
                st.caption(f"⏱️ Time: **{result.get('time_ms', 0)}ms**")
            with meta_col3:
                tool_count = len(result.get("tool_calls", []))
                st.caption(f"🔧 Tools: **{tool_count}**")
            
            # 工具调用详情
            if result.get("tool_calls"):
                with st.expander(f"🔧 View Tool Calls ({len(result['tool_calls'])})", expanded=False):
                    for i, tc in enumerate(result["tool_calls"], 1):
                        st.markdown(f"**Step {i}: {tc.get('tool')}**")
                        st.json(tc.get("parameters", {}))
                        if tc.get("result", {}).get("success"):
                            st.success("✅ Success")
                        else:
                            st.error(f"❌ {tc.get('result', {}).get('error', 'Failed')}")
                        st.divider()

        # 保存到历史
        assistant_msg = {
            "role": "assistant",
            "content": result["answer"],
            "tool_calls": result.get("tool_calls", []),
            "mode": result.get("mode"),
        }
        st.session_state.messages.append(assistant_msg)
        st.session_state.memory.add_message("assistant", result["answer"])
        st.session_state.stats.record_agent_call(result.get("mode", "unknown"))
        st.session_state.stats.save()

    # --- 导出功能 ---
    st.divider()
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📄 Export Markdown"):
            md = f"# Autonomous Agent Conversation\n\n**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n---\n\n"
            for msg in st.session_state.messages:
                role = "**User**" if msg["role"] == "user" else "**Agent**"
                md += f"{role}:\n\n{msg['content']}\n\n"
                if msg.get("tool_calls"):
                    md += f"*Tools used: {len(msg['tool_calls'])}*\n\n"
                md += "---\n\n"
            
            st.download_button(
                "⬇️ Download",
                md,
                file_name=f"agent_conversation_{datetime.now():%Y%m%d_%H%M%S}.md",
                mime="text/markdown",
            )
    
    with col2:
        if st.button("📊 View Stats JSON"):
            st.json(st.session_state.stats.to_dict())


if __name__ == "__main__":
    main()
