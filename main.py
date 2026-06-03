import streamlit as st
import sys
from pathlib import Path
from datetime import datetime
import json

sys.path.insert(0, str(Path(__file__).parent))

from app.config import AVAILABLE_MODELS, DEFAULT_MODEL, KNOWLEDGE_BASE_DIR
from app.memory.conversation import ConversationMemory, LongTermMemory
from app.agents.autonomous import run_agent
from app.agents.tasks import get_task_manager
from app.agents.learning import get_skill_learner
from app.rag.vectorstore import add_documents, list_collections, delete_collection
from app.utils.stats import get_stats, reset_stats


def main():
    st.set_page_config(page_title="Autonomous Agent Pro", page_icon="🤖", layout="wide")

    # Session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "memory" not in st.session_state:
        st.session_state.memory = ConversationMemory()
    if "current_model" not in st.session_state:
        st.session_state.current_model = DEFAULT_MODEL
    if "execution_mode" not in st.session_state:
        st.session_state.execution_mode = "auto"
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

        # 执行模式
        st.subheader("🧠 Execution Mode")
        mode = st.radio(
            "Mode",
            ["auto", "simple", "react", "multi"],
            format_func=lambda x: {
                "auto": "⚡ Auto",
                "simple": "💬 Simple",
                "react": "🔄 ReAct",
                "multi": "👥 Multi-Agent",
            }[x],
        )
        st.session_state.execution_mode = mode

        st.divider()

        # 使用统计
        st.subheader("📊 Statistics")
        stats = st.session_state.stats
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Tasks", stats.message_count)
            st.metric("Avg Time", f"{stats.total_time_ms // max(1, stats.message_count)}ms")
        with col2:
            st.metric("Tool Calls", sum(stats.agent_calls.values()))
            st.metric("Est. Tokens", f"{stats.total_tokens_estimate:,}")
        
        if st.button("Reset Stats"):
            reset_stats()
            st.session_state.stats = get_stats()
            st.rerun()

        st.divider()

        # 学习统计
        st.subheader("🎓 Learning")
        learner = get_skill_learner()
        learn_stats = learner.get_stats()
        st.write(f"Feedback: {learn_stats['total_feedback']}")
        st.write(f"Patterns: {learn_stats['learned_patterns']}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("👍", learn_stats["positive"])
        with col2:
            st.metric("👎", learn_stats["negative"])

        st.divider()

        # Knowledge Base
        st.subheader("📚 Knowledge Base")
        kb_collections = list_collections()
        st.write(f"Collections: {len(kb_collections)}")

        uploaded_files = st.file_uploader(
            "Add Documents",
            type=["txt", "md", "html", "py", "pdf"],
            accept_multiple_files=True,
        )
        if uploaded_files and st.button("Upload"):
            for f in uploaded_files:
                content = f.read().decode("utf-8", errors="ignore")
                add_documents("knowledge_base", [content], metadatas=[{"filename": f.name}])
            st.success(f"Added {len(uploaded_files)} docs")
            st.rerun()

        st.divider()

        # 任务管理
        st.subheader("📋 Tasks")
        task_mgr = get_task_manager()
        task_stats = task_mgr.get_stats()
        st.write(f"Active: {task_stats['active']} | Completed: {task_stats['completed']}")
        
        if st.button("Clear Conversation"):
            st.session_state.messages = []
            st.session_state.memory.clear()
            st.rerun()

    # --- Main Area ---
    st.title("🤖 Autonomous Agent Pro")
    st.caption("全能智能体 | 自主规划 · 多Agent协作 · 自我反思 · 持续学习 | NVIDIA NIM")

    # 标签页
    tab1, tab2, tab3 = st.tabs(["💬 Chat", "📋 Tasks", "📊 Analytics"])

    # === Tab 1: Chat ===
    with tab1:
        # 显示对话历史
        for i, msg in enumerate(st.session_state.messages):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
                # 显示元数据
                if msg.get("mode"):
                    meta_cols = st.columns(5)
                    meta_cols[0].caption(f"Mode: {msg['mode']}")
                    meta_cols[1].caption(f"⏱️ {msg.get('time_ms', 0)}ms")
                    if msg.get("tool_calls"):
                        meta_cols[2].caption(f"🔧 {len(msg['tool_calls'])} tools")
                    if msg.get("reflection"):
                        score = msg["reflection"].get("score", 0)
                        emoji = "✅" if msg["reflection"]["passed"] else "⚠️"
                        meta_cols[3].caption(f"{emoji} Score: {score}")
                
                # 工具调用详情
                if msg.get("tool_calls"):
                    with st.expander(f"🔧 Tool Calls ({len(msg['tool_calls'])})"):
                        for tc in msg["tool_calls"]:
                            st.json({
                                "tool": tc.get("tool"),
                                "parameters": tc.get("parameters"),
                            })
                
                # 反馈按钮（只在助手消息上显示）
                if msg["role"] == "assistant" and i == len(st.session_state.messages) - 1:
                    fb_col1, fb_col2, fb_col3 = st.columns([1, 1, 4])
                    
                    if fb_col1.button("👍 Good", key=f"good_{i}"):
                        learner.record_feedback(
                            task=st.session_state.messages[-2]["content"],
                            response=msg["content"],
                            feedback_type="positive",
                        )
                        st.success("Thanks for feedback!")
                    
                    if fb_col2.button("👎 Bad", key=f"bad_{i}"):
                        learner.record_feedback(
                            task=st.session_state.messages[-2]["content"],
                            response=msg["content"],
                            feedback_type="negative",
                        )
                        st.warning("Thanks for feedback. I'll improve!")

        # 用户输入
        if prompt := st.chat_input("Give me a task..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.memory.add_message("user", prompt)
            st.session_state.stats.record_message()
            
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                status = st.empty()
                status.info(f"🚀 Executing in **{mode}** mode...")
                
                history = st.session_state.memory.get_context_window()
                result = run_agent(
                    task=prompt,
                    model=st.session_state.current_model,
                    mode=mode,
                    history=history,
                )
                
                status.empty()
                st.markdown(result["answer"])
                
                # 元数据
                meta_col1, meta_col2, meta_col3, meta_col4 = st.columns(4)
                meta_col1.caption(f"🎯 {result.get('mode', 'unknown')}")
                meta_col2.caption(f"⏱️ {result.get('time_ms', 0)}ms")
                if result.get("tool_calls"):
                    meta_col3.caption(f"🔧 {len(result['tool_calls'])} tools")
                if result.get("reflection"):
                    score = result["reflection"].get("score", 0)
                    emoji = "✅" if result["reflection"]["passed"] else "⚠️"
                    meta_col4.caption(f"{emoji} Quality: {score}/10")
                
                # 工具详情
                if result.get("tool_calls"):
                    with st.expander(f"🔧 View Tools ({len(result['tool_calls'])})"):
                        for tc in result["tool_calls"]:
                            st.markdown(f"**{tc.get('tool')}**")
                            st.json(tc.get("parameters", {}))

            # 保存
            assistant_msg = {
                "role": "assistant",
                "content": result["answer"],
                "tool_calls": result.get("tool_calls", []),
                "mode": result.get("mode"),
                "time_ms": result.get("time_ms"),
                "reflection": result.get("reflection"),
            }
            st.session_state.messages.append(assistant_msg)
            st.session_state.memory.add_message("assistant", result["answer"])
            st.session_state.stats.save()

    # === Tab 2: Tasks ===
    with tab2:
        task_mgr = get_task_manager()
        
        # 任务创建
        st.subheader("Create New Task")
        new_task = st.text_input("Task description")
        task_mode = st.selectbox("Mode", ["immediate", "background", "scheduled"], index=0)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Create Task") and new_task:
                task_mgr.create_task(new_task, mode=task_mode)
                st.success("Task created!")
                st.rerun()
        
        with col2:
            if st.button("Clear All"):
                for t in task_mgr.list_tasks(limit=100):
                    task_mgr.delete_task(t["id"])
                st.rerun()
        
        
        st.divider()
        
        # 任务列表
        st.subheader("Task History")
        
        tasks = task_mgr.list_tasks(limit=10)
        if tasks:
            for task in tasks:
                with st.expander(f"**{task['task'][:50]}...** ({task['status']})"):
                    st.write(f"Mode: {task.get('mode', 'immediate')}")
                    st.write(f"Created: {task.get('created_at', 'N/A')}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Complete", key=f"complete_{task['id']}"):
                            task_mgr.complete_task(task["id"])
                            st.success("Task completed!")
                            st.rerun()
                    with col2:
                        if st.button("Delete", key=f"delete_{task['id']}"):
                            task_mgr.delete_task(task["id"])
                            st.rerun()
        else:
            st.info("No tasks yet. Create one above or start a conversation!")

    # === Tab 3: Analytics ===
    with tab3:
        st.subheader("Usage Analytics")
        
        # 统计图表
        stats = st.session_state.stats
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Agent Distribution")
            if stats.agent_calls:
                import pandas as pd
                df = pd.DataFrame([
                    {"Agent": k, "Calls": v}
                    for k, v in stats.agent_calls.items()
                ])
                st.bar_chart(df.set_index("Agent"))
            else:
                st.info("No data yet")
        
        with col2:
            st.markdown("#### Model Usage")
            if stats.model_calls:
                import pandas as pd
                df = pd.DataFrame([
                    {"Model": k.split("/")[-1][:20], "Calls": v}
                    for k, v in stats.model_calls.items()
                ])
                st.bar_chart(df.set_index("Model"))
            else:
                st.info("No data yet")
        
        st.divider()
        
        # 学习统计
        st.markdown("#### Learning Progress")
        learn_stats = learner.get_stats()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Feedback", learn_stats["total_feedback"])
        col2.metric("Learned Patterns", learn_stats["learned_patterns"])
        col3.metric("Corrections Applied", learn_stats["corrections"])
        
        # 导出
        st.divider()
        if st.button("📄 Export All Data"):
            export_data = {
                "stats": stats.to_dict(),
                "learning": learn_stats,
                "conversation_count": len(st.session_state.messages),
            }
            st.download_button(
                "⬇️ Download JSON",
                json.dumps(export_data, ensure_ascii=False, indent=2),
                file_name=f"agent_analytics_{datetime.now():%Y%m%d_%H%M%S}.json",
                mime="application/json",
            )


if __name__ == "__main__":
    main()
