import streamlit as st
import sys
import os
from pathlib import Path
from datetime import datetime
import io

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import AVAILABLE_MODELS, DEFAULT_MODEL, KNOWLEDGE_BASE_DIR
from app.memory.conversation import ConversationMemory, LongTermMemory
from app.agents.agents import process_message
from app.rag.vectorstore import add_documents, list_collections, delete_collection
from app.tools.document_parser import parse_file
from app.utils.stats import get_stats, reset_stats
from app.llm_client import chat_stream


def main():
    st.set_page_config(page_title="AI Agent Hub", page_icon="🤖", layout="wide")

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "memory" not in st.session_state:
        st.session_state.memory = ConversationMemory()
    if "current_model" not in st.session_state:
        st.session_state.current_model = DEFAULT_MODEL
    if "last_agent" not in st.session_state:
        st.session_state.last_agent = ""
    if "last_time_ms" not in st.session_state:
        st.session_state.last_time_ms = 0
    if "stats" not in st.session_state:
        st.session_state.stats = get_stats()

    # --- Sidebar ---
    with st.sidebar:
        st.header("⚙️ Settings")

        # Model selection
        model_label = st.selectbox(
            "Model",
            list(AVAILABLE_MODELS.keys()),
            index=list(AVAILABLE_MODELS.keys()).index("DeepSeek V4 Flash"),
        )
        st.session_state.current_model = AVAILABLE_MODELS[model_label]

        st.divider()

        # 使用统计面板
        st.subheader("📊 Usage Stats")
        stats = st.session_state.stats
        col1, col2 = st.columns(2)
        with col1:
            st.metric("API Calls", stats.api_calls)
            st.metric("Messages", stats.message_count)
        with col2:
            st.metric("Est. Tokens", f"{stats.total_tokens_estimate:,}")
            st.metric("Avg Time", f"{stats.total_time_ms // max(1, stats.api_calls)}ms")
        
        # Agent分布
        if stats.agent_calls:
            st.caption("Agent Distribution:")
            for agent, count in stats.agent_calls.items():
                st.caption(f"  • {agent}: {count}")
        
        if st.button("Reset Stats"):
            reset_stats()
            st.session_state.stats = get_stats()
            st.rerun()

        st.divider()

        # Knowledge base management
        st.subheader("📚 Knowledge Base")
        kb_collections = list_collections()
        st.write(f"Collections: {len(kb_collections)}")
        for col_name in kb_collections:
            col1, col2 = st.columns([3, 1])
            col1.write(f"• {col_name}")
            if col2.button("Delete", key=f"del_{col_name}"):
                delete_collection(col_name)
                st.rerun()

        uploaded_files = st.file_uploader(
            "Upload documents",
            type=["txt", "md", "html", "py", "pdf"],
            accept_multiple_files=True,
        )
        if uploaded_files and st.button("Add to Knowledge Base"):
            for f in uploaded_files:
                content = f.read().decode("utf-8", errors="ignore")
                add_documents("knowledge_base", [content], metadatas=[{"filename": f.name}])
                (KNOWLEDGE_BASE_DIR / f.name).write_text(content, encoding="utf-8")
            st.success(f"Added {len(uploaded_files)} documents")
            st.rerun()

        st.divider()

        # Memory management
        st.subheader("🧠 Memory")
        if st.button("Clear Conversation"):
            st.session_state.messages = []
            st.session_state.memory.clear()
            st.rerun()

        if st.button("Clear Long-term Memory"):
            LongTermMemory().clear()
            st.success("Long-term memory cleared")

        st.divider()

        # Agent状态显示
        if st.session_state.last_agent:
            st.caption(f"Last agent: **{st.session_state.last_agent}**")
            st.caption(f"Response time: **{st.session_state.last_time_ms}ms**")

    # --- Main Chat Area ---
    st.title("🤖 AI Agent Hub")
    st.caption("Multi-agent system powered by NVIDIA NIM | Researcher · Coder · Analyst | 🚀 Optimized")

    # 显示对话历史
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 用户输入
    if prompt := st.chat_input("Ask me anything..."):
        # 记录用户消息
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.memory.add_message("user", prompt)
        st.session_state.stats.record_message()
        
        with st.chat_message("user"):
            st.markdown(prompt)

        # 处理响应
        with st.chat_message("assistant"):
            # 🔧 优化: 显示Agent路由过程
            status_placeholder = st.empty()
            status_placeholder.info("🔄 Routing to appropriate agent...")
            
            with st.spinner("Processing..."):
                history = st.session_state.memory.get_context_window()
                result = process_message(
                    prompt,
                    model=st.session_state.current_model,
                    history=history,
                )

                # 更新统计
                st.session_state.last_agent = result["agent"]
                st.session_state.last_time_ms = result.get("time_ms", 0)
                st.session_state.stats.record_agent_call(result["agent"])
                st.session_state.stats.record_api_call(
                    st.session_state.current_model,
                    len(result["response"]) // 4,  # 粗略估算token
                    result.get("time_ms", 0),
                )

                # 清除状态，显示响应
                status_placeholder.empty()
                response_text = result["response"]
                st.markdown(response_text)

            # Agent标签
            st.caption(f"🤖 **{result['agent'].upper()}** | ⏱️ {result.get('time_ms', 0)}ms")

        # 保存到历史
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        st.session_state.memory.add_message("assistant", response_text)
        st.session_state.stats.save()  # 持久化统计

    # --- 对话导出功能 ---
    st.divider()
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📄 Export as Markdown"):
            md_content = f"# AI Agent Hub Conversation\n\n"
            md_content += f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            md_content += f"**Model:** {model_label}\n\n"
            md_content += "---\n\n"
            
            for msg in st.session_state.messages:
                role = "**User**" if msg["role"] == "user" else "**Assistant**"
                md_content += f"{role}:\n\n{msg['content']}\n\n---\n\n"
            
            # 下载按钮
            st.download_button(
                label="⬇️ Download Markdown",
                data=md_content,
                file_name=f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown",
            )
    
    with col2:
        if st.button("📊 Export as JSON"):
            json_data = {
                "date": datetime.now().isoformat(),
                "model": model_label,
                "messages": st.session_state.messages,
                "stats": st.session_state.stats.to_dict(),
            }
            import json
            st.download_button(
                label="⬇️ Download JSON",
                data=json.dumps(json_data, ensure_ascii=False, indent=2),
                file_name=f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
            )


if __name__ == "__main__":
    main()
