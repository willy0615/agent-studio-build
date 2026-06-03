"""增强版主界面 - 集成所有新功能"""
import streamlit as st
import sys
from pathlib import Path
from datetime import datetime
import json
import tempfile
import os

sys.path.insert(0, str(Path(__file__).parent))

from app.config import AVAILABLE_MODELS, DEFAULT_MODEL, KNOWLEDGE_BASE_DIR
from app.memory.conversation import ConversationMemory, LongTermMemory
from app.agents.autonomous import run_agent, run_agent_stream
from app.agents.tasks import get_task_manager
from app.agents.learning import get_skill_learner
from app.agents.workflow import get_orchestrator
from app.agents.scheduler import get_scheduler, CRON_PRESETS
from app.rag.vectorstore import add_documents, list_collections, delete_collection
from app.utils.stats import get_stats, reset_stats
from app.utils.cache import get_cache
from app.tools.tool_registry import ToolRegistry


def main():
    st.set_page_config(
        page_title="Autonomous Agent Pro - Enhanced",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # === Session State ===
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
    if "use_cache" not in st.session_state:
        st.session_state.use_cache = True
    if "use_stream" not in st.session_state:
        st.session_state.use_stream = False
    if "uploaded_files_context" not in st.session_state:
        st.session_state.uploaded_files_context = {}

    # === Sidebar ===
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

        # 性能选项
        st.subheader("⚡ Performance")
        use_cache = st.checkbox("启用缓存", value=True)
        use_stream = st.checkbox("流式输出", value=False)
        st.session_state.use_cache = use_cache
        st.session_state.use_stream = use_stream

        st.divider()

        # === 缓存统计 ===
        if use_cache:
            st.subheader("💾 Cache Stats")
            cache = get_cache()
            cache_stats = cache.get_stats()
            
            col1, col2 = st.columns(2)
            col1.metric("命中率", cache_stats["hit_rate"])
            col2.metric("缓存大小", cache_stats["cache_size"])
            
            if st.button("清空缓存"):
                cache.clear()
                st.rerun()
            
            st.divider()

        # === 统计 ===
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

        # === 学习统计 ===
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

        # === Knowledge Base ===
        st.subheader("📚 Knowledge Base")
        kb_collections = list_collections()
        st.write(f"Collections: {len(kb_collections)}")

        uploaded_files = st.file_uploader(
            "Add Documents",
            type=["txt", "md", "html", "py", "pdf", "docx", "xlsx", "csv"],
            accept_multiple_files=True,
        )
        if uploaded_files and st.button("Upload"):
            for f in uploaded_files:
                content = f.read().decode("utf-8", errors="ignore")
                add_documents("knowledge_base", [content], metadatas=[{"filename": f.name}])
            st.success(f"Added {len(uploaded_files)} docs")
            st.rerun()

        st.divider()

        # === 任务管理 ===
        st.subheader("📋 Tasks")
        task_mgr = get_task_manager()
        task_stats = task_mgr.get_stats()
        st.write(f"Active: {task_stats['active']} | Completed: {task_stats['completed']}")
        
        if st.button("Clear Conversation"):
            st.session_state.messages = []
            st.session_state.memory.clear()
            st.rerun()

    # === Main Area ===
    st.title("🤖 Autonomous Agent Pro")
    st.caption("全能智能体 | 自主规划 · 多Agent协作 · 自我反思 · 持续学习 | NVIDIA NIM")
    
    # 功能标签
    st.markdown("""
    **新增功能**: 🖼️ 图像分析 | 📊 数据分析 | 🎤 语音处理 | 🌐 网页自动化 | 🔔 通知系统 | ⚡ 工具链 | ⏰ 任务调度
    """)

    # === 标签页 ===
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💬 Chat",
        "🛠️ Tools",
        "🔗 Chains",
        "⏰ Scheduler",
        "📊 Analytics",
    ])

    # ========================================
    # Tab 1: Chat
    # ========================================
    with tab1:
        # === 文件上传区 ===
        st.subheader("📤 上传文件（可选）")
        
        upload_col1, upload_col2, upload_col3 = st.columns(3)
        
        with upload_col1:
            # 图像上传
            image_file = st.file_uploader("🖼️ 图像", type=["jpg", "jpeg", "png", "gif"])
            if image_file:
                st.image(image_file, use_column_width=True)
                # 保存到临时文件
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                temp_file.write(image_file.read())
                temp_file.close()
                st.session_state.uploaded_files_context["image"] = temp_file.name
        
        with upload_col2:
            # 数据文件上传
            data_file = st.file_uploader("📊 数据文件", type=["xlsx", "xls", "csv"])
            if data_file:
                # 保存到临时文件
                suffix = Path(data_file.name).suffix
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                temp_file.write(data_file.read())
                temp_file.close()
                st.session_state.uploaded_files_context["data"] = temp_file.name
                st.info(f"已加载: {data_file.name}")
        
        with upload_col3:
            # 文档上传
            doc_file = st.file_uploader("📄 文档", type=["pdf", "docx", "txt"])
            if doc_file:
                suffix = Path(doc_file.name).suffix
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                temp_file.write(doc_file.read())
                temp_file.close()
                st.session_state.uploaded_files_context["document"] = temp_file.name
                st.info(f"已加载: {doc_file.name}")
        
        st.divider()

        # === 对话历史 ===
        for i, msg in enumerate(st.session_state.messages):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
                # 元数据
                if msg.get("mode"):
                    meta_cols = st.columns(5)
                    meta_cols[0].caption(f"Mode: {msg['mode']}")
                    meta_cols[1].caption(f"⏱️ {msg.get('time_ms', 0)}ms")
                    if msg.get("tool_calls"):
                        meta_cols[2].caption(f"🔧 {len(msg['tool_calls'])} tools")
                    if msg.get("cached"):
                        meta_cols[3].caption("💾 Cached")
                    if msg.get("reflection"):
                        score = msg["reflection"].get("score", 0)
                        emoji = "✅" if msg["reflection"]["passed"] else "⚠️"
                        meta_cols[4].caption(f"{emoji} Score: {score}")
                
                # 工具调用详情
                if msg.get("tool_calls"):
                    with st.expander(f"🔧 Tool Calls ({len(msg['tool_calls'])})"):
                        for tc in msg["tool_calls"]:
                            st.markdown(f"**{tc.get('tool')}**")
                            st.json(tc.get("parameters", {}))
                
                # 反馈按钮
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

        # === 用户输入 ===
        if prompt := st.chat_input("Give me a task..."):
            # 构建完整提示
            full_prompt = prompt
            
            # 添加文件上下文
            if st.session_state.uploaded_files_context:
                context_parts = []
                
                if "image" in st.session_state.uploaded_files_context:
                    image_path = st.session_state.uploaded_files_context["image"]
                    # 分析图像
                    with st.spinner("正在分析图像..."):
                        img_result = ToolRegistry.execute(
                            "analyze_image",
                            image_path=image_path,
                            question="描述这张图片的内容",
                        )
                        if img_result.get("success"):
                            context_parts.append(f"[图像内容]: {img_result['result']}")
                
                if "data" in st.session_state.uploaded_files_context:
                    data_path = st.session_state.uploaded_files_context["data"]
                    # 分析数据
                    with st.spinner("正在分析数据..."):
                        data_result = ToolRegistry.execute(
                            "analyze_data",
                            file_path=data_path,
                            analysis_type="summary",
                        )
                        if data_result.get("success"):
                            context_parts.append(f"[数据摘要]: {data_result['result']}")
                
                if "document" in st.session_state.uploaded_files_context:
                    doc_path = st.session_state.uploaded_files_context["document"]
                    # 解析文档
                    with st.spinner("正在解析文档..."):
                        doc_result = ToolRegistry.execute(
                            "parse_document",
                            file_path=doc_path,
                        )
                        if doc_result.get("success"):
                            context_parts.append(f"[文档内容]: {doc_result['result'][:1000]}...")
                
                if context_parts:
                    full_prompt = f"{prompt}\n\n" + "\n\n".join(context_parts)
            
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.memory.add_message("user", prompt)
            st.session_state.stats.record_message()
            
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                status = st.empty()
                status.info(f"🚀 Executing in **{mode}** mode...")
                
                history = st.session_state.memory.get_context_window()
                
                # 选择执行方式
                if use_stream and mode == "simple":
                    # 流式输出
                    placeholder = st.empty()
                    full_response = ""
                    
                    for chunk in run_agent_stream(
                        task=full_prompt,
                        model=st.session_state.current_model,
                        mode=mode,
                        history=history,
                    ):
                        full_response += chunk
                        placeholder.markdown(full_response + "▌")
                    
                    placeholder.markdown(full_response)
                    result = {
                        "answer": full_response,
                        "mode": "stream",
                        "time_ms": 0,
                    }
                else:
                    # 常规执行（带缓存）
                    result = run_agent(
                        task=full_prompt,
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
                if result.get("cached"):
                    meta_col4.caption("💾 Cached")
                
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
                "cached": result.get("cached", False),
            }
            st.session_state.messages.append(assistant_msg)
            st.session_state.memory.add_message("assistant", result["answer"])
            st.session_state.stats.save()
            
            # 清理上传的文件
            st.session_state.uploaded_files_context = {}

    # ========================================
    # Tab 2: Tools
    # ========================================
    with tab2:
        st.subheader("🛠️ 可用工具")
        
        tools = ToolRegistry.list_tools()
        
        # 分类显示
        categories = {
            "核心工具": ["web_search", "fetch_url", "execute_code", "calculate"],
            "文件操作": ["read_file", "write_file", "list_directory"],
            "文档处理": ["parse_document"],
            "图像分析": ["analyze_image", "extract_text_from_image"],
            "数据分析": ["analyze_data", "create_chart", "process_excel"],
            "语音处理": ["transcribe_audio", "text_to_speech"],
            "网页自动化": ["browse_website", "download_file"],
            "通知系统": ["send_email", "send_webhook", "send_notification"],
        }
        
        for category, tool_names in categories.items():
            with st.expander(f"**{category}** ({len(tool_names)}个工具)"):
                for tool in tools:
                    if tool["name"] in tool_names:
                        st.markdown(f"**{tool['name']}**: {tool['description'][:50]}...")
        
        # 快速测试
        st.divider()
        st.subheader("🧪 快速测试工具")
        
        test_tool = st.selectbox("选择工具", [t["name"] for t in tools])
        
        if test_tool:
            tool_info = ToolRegistry.get_tool(test_tool)
            if tool_info:
                st.markdown(f"**描述**: {tool_info['description']}")
                st.markdown("**参数**:")
                st.json(tool_info["parameters"])

    # ========================================
    # Tab 3: Chains
    # ========================================
    with tab3:
        st.subheader("🔗 工具链")
        
        orchestrator = get_orchestrator()
        chains = orchestrator.list_chains()
        
        st.markdown("预定义工具链:")
        for chain in chains:
            with st.expander(f"**{chain['name']}** ({chain['steps']}步)"):
                st.markdown(f"**工具序列**: {' → '.join(chain['step_tools'])}")
        
        # 执行工具链
        st.divider()
        st.subheader("执行工具链")
        
        chain_name = st.selectbox("选择工具链", [c["name"] for c in chains])
        chain_input = st.text_area("输入参数 (JSON格式)", "{}")
        
        if st.button("执行工具链"):
            try:
                inputs = json.loads(chain_input)
                result = orchestrator.execute_chain(chain_name, inputs)
                
                if result["success"]:
                    st.success("✅ 执行成功!")
                    st.json(result["final_result"])
                else:
                    st.error(f"❌ 执行失败: {result.get('error')}")
            except json.JSONDecodeError:
                st.error("Invalid JSON input")

    # ========================================
    # Tab 4: Scheduler
    # ========================================
    with tab4:
        st.subheader("⏰ 任务调度")
        
        scheduler = get_scheduler()
        
        # 创建定时任务
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 创建定时任务")
            
            task_desc = st.text_input("任务描述")
            task_type = st.selectbox("任务类型", ["提醒", "报告"])
            
            if task_type == "提醒":
                reminder_msg = st.text_area("提醒内容")
                delay_min = st.number_input("延迟（分钟）", min_value=1, value=60)
                
                if st.button("创建提醒"):
                    result = scheduler.schedule_reminder(
                        message=reminder_msg,
                        delay_minutes=delay_min,
                    )
                    if result["success"]:
                        st.success(f"✅ 提醒已创建，将在 {result['scheduled_time']} 执行")
                    else:
                        st.error(f"❌ 创建失败: {result.get('error')}")
        
        with col2:
            st.markdown("### Cron预设")
            
            cron_preset = st.selectbox("选择预设", list(CRON_PRESETS.keys()))
            st.code(f"{cron_preset}: {CRON_PRESETS[cron_preset]}", language="text")
        
        st.divider()
        
        # 已调度任务
        st.markdown("### 已调度任务")
        scheduled_tasks = scheduler.list_scheduled_tasks()
        
        if scheduled_tasks:
            for task in scheduled_tasks:
                with st.expander(f"**{task['id']}** - {task['status']}"):
                    st.write(f"描述: {task['description']}")
                    st.write(f"执行时间: {task['scheduled_time']}")
                    st.write(f"重复: {task['repeat']}")
                    
                    if st.button("取消", key=f"cancel_{task['id']}"):
                        scheduler.cancel_task(task["id"])
                        st.rerun()
        else:
            st.info("暂无已调度任务")

    # ========================================
    # Tab 5: Analytics
    # ========================================
    with tab5:
        st.subheader("📊 分析报告")
        
        # 统计图表
        stats = st.session_state.stats
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("总任务数", stats.message_count)
        
        with col2:
            st.metric("总工具调用", sum(stats.agent_calls.values()))
        
        with col3:
            if stats.message_count > 0:
                avg_time = stats.total_time_ms // stats.message_count
                st.metric("平均耗时", f"{avg_time}ms")
        
        st.divider()
        
        # Agent分布
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Agent调用分布")
            if stats.agent_calls:
                import pandas as pd
                df = pd.DataFrame([
                    {"Agent": k, "Calls": v}
                    for k, v in stats.agent_calls.items()
                ])
                st.bar_chart(df.set_index("Agent"))
            else:
                st.info("暂无数据")
        
        with col2:
            st.markdown("#### 模型调用分布")
            if stats.model_calls:
                import pandas as pd
                df = pd.DataFrame([
                    {"Model": k.split("/")[-1][:20], "Calls": v}
                    for k, v in stats.model_calls.items()
                ])
                st.bar_chart(df.set_index("Model"))
            else:
                st.info("暂无数据")
        
        st.divider()
        
        # 学习统计
        st.markdown("#### 学习进度")
        learn_stats = learner.get_stats()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("总反馈", learn_stats["total_feedback"])
        col2.metric("学习模式", learn_stats["learned_patterns"])
        col3.metric("应用修正", learn_stats["corrections"])
        
        # 缓存统计
        if use_cache:
            st.divider()
            st.markdown("#### 缓存统计")
            cache = get_cache()
            cache_stats = cache.get_stats()
            
            col1, col2, col3 = st.columns(3)
            col1.metric("缓存命中", cache_stats["hits"])
            col2.metric("缓存未命中", cache_stats["misses"])
            col3.metric("命中率", cache_stats["hit_rate"])
        
        # 导出
        st.divider()
        if st.button("📄 导出所有数据"):
            export_data = {
                "stats": stats.to_dict(),
                "learning": learn_stats,
                "cache": cache.get_stats() if use_cache else {},
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
