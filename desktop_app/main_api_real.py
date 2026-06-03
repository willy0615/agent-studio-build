#!/usr/bin/env python3
"""
Agent Studio - 智能体桌面应用（完整版）
功能：连接真实Agent后端 + 完整任务/统计/设置页面
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QComboBox, QLineEdit, QCheckBox,
    QListWidget, QListWidgetItem, QStackedWidget, QTableWidget, QTableWidgetItem,
    QFrame, QScrollArea, QHeaderView, QProgressBar, QGroupBox, QTabWidget,
    QFileDialog, QMessageBox, QSplitter, QFormLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QColor, QPalette, QFont


# ============================================================
# 消息气泡组件
# ============================================================
class MessageBubble(QFrame):
    def __init__(self, text, is_user=True, metadata=None, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        if is_user:
            main_layout.addStretch(3)
            content_layout = QVBoxLayout()
            content_layout.setContentsMargins(0, 0, 12, 0)
            content_layout.setSpacing(2)
            
            header = QHBoxLayout()
            header.addStretch()
            name_label = QLabel("我")
            name_label.setStyleSheet("color: #8ab4f8; font-size: 12px; font-weight: bold; background: transparent;")
            header.addWidget(name_label)
            content_layout.addLayout(header)
            
            bubble = QFrame()
            bubble.setFrameShape(QFrame.Shape.Box)
            bubble.setLineWidth(1)
            bubble.setStyleSheet("""
                QFrame {
                    background-color: #1f4d7a;
                    border: 1px solid #2d5a8a;
                    border-radius: 12px;
                }
            """)
            bl = QVBoxLayout(bubble)
            bl.setContentsMargins(12, 10, 12, 10)
            
            msg = QLabel(text)
            msg.setWordWrap(True)
            msg.setStyleSheet("color: #e1e4e8; font-size: 14px; background: transparent; line-height: 1.5;")
            bl.addWidget(msg)
            content_layout.addWidget(bubble)
            main_layout.addLayout(content_layout)
        else:
            content_layout = QVBoxLayout()
            content_layout.setContentsMargins(12, 0, 0, 0)
            content_layout.setSpacing(2)
            
            header = QHBoxLayout()
            avatar = QLabel("🤖")
            avatar.setFixedSize(28, 28)
            avatar.setStyleSheet("font-size: 20px; background: transparent;")
            avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            header.addWidget(avatar)
            
            name_label = QLabel("智能体")
            name_label.setStyleSheet("color: #58a6ff; font-size: 12px; font-weight: bold; background: transparent;")
            header.addWidget(name_label)
            
            if metadata and metadata.get("mode"):
                mode_label = QLabel(f"[{metadata['mode']}]")
                mode_label.setStyleSheet("color: #8b949e; font-size: 11px; background: transparent;")
                header.addWidget(mode_label)
            
            header.addStretch()
            content_layout.addLayout(header)
            
            bubble = QFrame()
            bubble.setFrameShape(QFrame.Shape.Box)
            bubble.setLineWidth(0)
            bubble.setStyleSheet("""
                QFrame {
                    background-color: #21262d;
                    border: 1px solid #30363d;
                    border-radius: 12px;
                }
            """)
            bl = QVBoxLayout(bubble)
            bl.setContentsMargins(12, 10, 12, 10)
            
            msg = QLabel(text)
            msg.setWordWrap(True)
            msg.setStyleSheet("color: #c9d1d9; font-size: 14px; background: transparent; line-height: 1.5;")
            bl.addWidget(msg)
            
            # 添加元数据信息
            if metadata:
                meta_text = []
                if metadata.get("time_ms"):
                    meta_text.append(f"⏱ {metadata['time_ms']}ms")
                if metadata.get("tool_calls"):
                    meta_text.append(f"🔧 {len(metadata['tool_calls'])}次工具调用")
                if meta_text:
                    meta_label = QLabel(" | ".join(meta_text))
                    meta_label.setStyleSheet("color: #6e7681; font-size: 11px; background: transparent; margin-top: 8px;")
                    bl.addWidget(meta_label)
            
            content_layout.addWidget(bubble)
            main_layout.addLayout(content_layout)
            main_layout.addStretch(3)
        
        self.setStyleSheet("QFrame { background: transparent; }")


# ============================================================
# Agent工作线程 - 调用真实 NVIDIA API
# ============================================================
class AgentWorker(QThread):
    result_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    progress_update = pyqtSignal(str)
    
    def __init__(self, task, model="deepseek-ai/deepseek-v4-flash", mode="auto", context="", history=None):
        super().__init__()
        self.task = task
        self.model = model
        self.mode = mode
        self.context = context
        self.history = history or []
    
    def run(self):
        import time
        import os
        from pathlib import Path
        
        start_time = time.time()
        
        try:
            # 读取 API 配置
            api_key = ""
            base_url = "https://integrate.api.nvidia.com/v1"
            
            # 从 .env 读取
            from dotenv import load_dotenv
            load_dotenv()
            
            api_key = os.getenv("NVIDIA_API_KEY", "")
            base_url = os.getenv("NVIDIA_BASE_URL", base_url)
            
            # 从用户配置读取
            settings_file = Path.home() / ".agent_studio" / "settings.env"
            if settings_file.exists():
                load_dotenv(settings_file)
                api_key = os.getenv("NVIDIA_API_KEY", api_key)
                base_url = os.getenv("NVIDIA_BASE_URL", base_url)
            
            if not api_key:
                self.error_occurred.emit("API Key 未配置，请在设置页面配置 NVIDIA_API_KEY")
                return
            
            self.progress_update.emit("正在连接 NVIDIA API...")
            
            # 使用 OpenAI SDK
            try:
                from openai import OpenAI
            except ImportError:
                self.error_occurred.emit("openai 库未安装，请运行: pip install openai")
                return
            
            client = OpenAI(api_key=api_key, base_url=base_url)
            
            # 构建消息历史
            messages = []
            for msg in self.history:
                if msg.get("role") in ["user", "assistant"]:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            # 添加当前任务
            if self.context:
                messages.append({
                    "role": "system",
                    "content": f"上下文: {self.context}"
                })
            
            messages.append({"role": "user", "content": self.task})
            
            self.progress_update.emit(f"正在调用模型: {self.model}...")
            
            # 调用 API
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
                stream=False
            )
            
            elapsed = int((time.time() - start_time) * 1000)
            answer = response.choices[0].message.content
            
            # 模拟工具调用（根据模式）
            tool_calls = []
            if self.mode == "react":
                tool_calls = ["web_search", "code_executor"]  # 模拟
            elif self.mode == "multi":
                tool_calls = ["researcher_agent", "coder_agent"]
            
            result = {
                "success": True,
                "answer": answer,
                "mode": self.mode,
                "time_ms": elapsed,
                "tool_calls": tool_calls,
                "backend_connected": True,
                "model": self.model
            }
            
            self.progress_update.emit(f"完成 ({elapsed}ms)")
            self.result_ready.emit(result)
            
        except Exception as e:
            import traceback
            elapsed = int((time.time() - start_time) * 1000)
            error_msg = f"{str(e)}\n\n{traceback.format_exc()}"
            self.error_occurred.emit(error_msg)
\n
class AgentWorker(QThread):
    result_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    progress_update = pyqtSignal(str)
    
    def __init__(self, task, model="qclaw/modelroute", mode="auto", context="", history=None):
        super().__init__()
        self.task = task
        self.model = model
        self.mode = mode
        self.context = context
        self.history = history or []
        self.backend_available = False
    
    def run(self):
        import time
        start_time = time.time()
        
        try:
            # 尝试导入真实后端
            try:
                from app.agents.autonomous import AutonomousAgent
                self.backend_available = True
                self.progress_update.emit("后端已连接")
            except ImportError as e:
                self.progress_update.emit(f"后端导入失败: {str(e)[:50]}")
            
            if self.backend_available:
                self.progress_update.emit("正在初始化Agent...")
                agent = AutonomousAgent(model=self.model, mode=self.mode)
                
                self.progress_update.emit("正在分析任务...")
                result = agent.run(
                    task=self.task,
                    context=self.context,
                    history=self.history,
                    enable_reflection=True,
                    enable_learning=True
                )
                
                elapsed = int((time.time() - start_time) * 1000)
                result["time_ms"] = elapsed
                self.result_ready.emit(result)
            else:
                # 模拟模式 - 但显示真实连接信息
                time.sleep(1)
                elapsed = int((time.time() - start_time) * 1000)
                
                answer = f"""⚠️ 后端未连接

当前为模拟模式。要连接真实后端，请确保：

1. 后端目录存在: E:\AgentProject\app
2. 已安装依赖: pip install -r requirements.txt  
3. 已配置API Key: 在 .env 文件中设置 NVIDIA_API_KEY
4. Python路径正确: {sys.path[0]}

任务信息:
- 任务: {self.task}
- 模型: {self.model}
- 模式: {self.mode}
- 执行时间: {elapsed}ms"""
                
                result = {
                    "success": True,
                    "answer": answer,
                    "mode": self.mode,
                    "time_ms": elapsed,
                    "tool_calls": [],
                    "backend_connected": False
                }
                self.result_ready.emit(result)
                
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n\n{traceback.format_exc()}"
            self.error_occurred.emit(error_msg)


# ============================================================
# 聊天页面
# ============================================================
class ChatPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.history = []
        self.current_model = "qclaw/modelroute"
        self.execution_mode = "auto"
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 顶部工具栏
        top_bar = QFrame()
        top_bar.setFrameShape(QFrame.Shape.NoFrame)
        top_bar.setFixedHeight(50)
        top_bar.setStyleSheet("QFrame { background: #161b22; border-bottom: 1px solid #30363d; }")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(16, 0, 16, 0)
        top_layout.setSpacing(12)
        
        # 模型选择
        model_label = QLabel("🤖 模型:")
        model_label.setStyleSheet("color: #c9d1d9; background: transparent;")
        top_layout.addWidget(model_label)
        
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "qclaw/modelroute",
            "deepseek-ai/deepseek-v4-flash",
            "deepseek-ai/deepseek-v4-pro",
            "z-ai/glm-5.1",
            "nvidia/nemotron-3-120b"
        ])
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        self.model_combo.setFixedWidth(220)
        self.model_combo.setStyleSheet(self._combo_style())
        top_layout.addWidget(self.model_combo)
        
        top_layout.addSpacing(20)
        
        # 模式选择
        mode_label = QLabel("⚙️ 模式:")
        mode_label.setStyleSheet("color: #c9d1d9; background: transparent;")
        top_layout.addWidget(mode_label)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["auto", "simple", "react", "multi"])
        self.mode_combo.setItemText(0, "自动选择")
        self.mode_combo.setItemText(1, "简单问答")
        self.mode_combo.setItemText(2, "ReAct推理")
        self.mode_combo.setItemText(3, "多Agent协作")
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        self.mode_combo.setFixedWidth(130)
        self.mode_combo.setStyleSheet(self._combo_style())
        top_layout.addWidget(self.mode_combo)
        
        top_layout.addStretch()
        
        # 状态标签
        self.status_label = QLabel("✅ 就绪")
        self.status_label.setStyleSheet("color: #3fb950; font-size: 12px; background: transparent; padding: 4px 12px; border-radius: 4px;")
        top_layout.addWidget(self.status_label)
        
        layout.addWidget(top_bar)
        
        # 消息区域
        self.message_container = QWidget()
        self.message_layout = QVBoxLayout(self.message_container)
        self.message_layout.setContentsMargins(20, 16, 20, 16)
        self.message_layout.setSpacing(16)
        self.message_layout.addStretch()
        
        self.scroll = QScrollArea()
        self.scroll.setWidget(self.message_container)
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { background: #0d1117; border: none; }")
        layout.addWidget(self.scroll, stretch=1)
        
        # 输入区域
        input_frame = QFrame()
        input_frame.setFrameShape(QFrame.Shape.NoFrame)
        input_frame.setStyleSheet("QFrame { background: #161b22; border-top: 1px solid #30363d; }")
        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(16, 12, 16, 12)
        input_layout.setSpacing(8)
        
        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("输入消息，按 Ctrl+Enter 发送...")
        self.input_field.setMaximumHeight(120)
        self.input_field.setMinimumHeight(50)
        self.input_field.setStyleSheet("""
            QTextEdit {
                background: #0d1117;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 10px 12px;
                font-size: 14px;
                selection-background-color: #264f78;
            }
            QTextEdit:focus {
                border: 1px solid #388bfd;
            }
        """)
        input_layout.addWidget(self.input_field)
        
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        
        # 快捷操作
        self.clear_btn = QPushButton("🗑️ 清空")
        self.clear_btn.setFixedSize(80, 36)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background: #21262d;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover { background: #30363d; }
        """)
        self.clear_btn.clicked.connect(self.clear_chat)
        btn_row.addWidget(self.clear_btn)
        
        btn_row.addStretch()
        
        self.send_btn = QPushButton("发送 ➤")
        self.send_btn.setFixedSize(100, 40)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background: #238636;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background: #2ea043; }
            QPushButton:pressed { background: #238636; }
            QPushButton:disabled {
                background: #21262d;
                color: #484f58;
            }
        """)
        self.send_btn.clicked.connect(self.send_message)
        btn_row.addWidget(self.send_btn)
        input_layout.addLayout(btn_row)
        layout.addWidget(input_frame)
        
        # 欢迎消息
        self.add_message("你好！我是 Agent Studio，一个全能型AI助手。\n\n我可以帮你：\n• 🔍 搜索信息、调研分析\n• 💻 编写代码、调试程序\n• 📊 数据分析、生成报告\n• 📝 写作翻译、内容创作\n\n有什么可以帮你的吗？", is_user=False)
    
    def _combo_style(self):
        return """
            QComboBox {
                background: #0d1117;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QComboBox::drop-down { border: none; width: 20px; }
            QComboBox QAbstractItemView {
                background: #0d1117;
                color: #c9d1d9;
                border: 1px solid #30363d;
                selection-background-color: #1f6feb;
                padding: 4px;
            }
        """
    
    def on_model_changed(self, text):
        self.current_model = text
    
    def on_mode_changed(self, text):
        self.execution_mode = text
    
    def add_message(self, text, is_user=True, metadata=None):
        bubble = MessageBubble(text, is_user, metadata)
        self.message_layout.insertWidget(self.message_layout.count() - 1, bubble)
        sb = self.scroll.verticalScrollBar()
        sb.setValue(sb.maximum())
    
    def send_message(self):
        text = self.input_field.toPlainText().strip()
        if not text:
            return
        
        self.add_message(text, is_user=True)
        self.input_field.clear()
        self.send_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.status_label.setText("⏳ 执行中...")
        self.status_label.setStyleSheet("color: #d29922; font-size: 12px; background: transparent;")
        
        self.worker = AgentWorker(
            task=text,
            model=self.current_model,
            mode=self.execution_mode,
            history=self.history
        )
        self.worker.result_ready.connect(self.on_result)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.progress_update.connect(self.on_progress)
        self.worker.start()
    
    def on_progress(self, msg):
        self.status_label.setText(f"⏳ {msg}")
    
    def on_result(self, result):
        metadata = {
            "mode": result.get("mode", "unknown"),
            "time_ms": result.get("time_ms", 0),
            "tool_calls": result.get("tool_calls", [])
        }
        self.add_message(result["answer"], is_user=False, metadata=metadata)
        
        # 更新历史
        self.history.append({"role": "user", "content": self.worker.task})
        self.history.append({"role": "assistant", "content": result["answer"]})
        
        ms = result.get("time_ms", 0)
        mode = result.get("mode", "unknown")
        self.status_label.setText(f"✅ 已完成 | {mode} | {ms}ms")
        self.status_label.setStyleSheet("color: #3fb950; font-size: 12px; background: transparent;")
        self.send_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
    
    def on_error(self, msg):
        self.add_message(f"❌ 执行出错:\n\n{msg}", is_user=False)
        self.status_label.setText("❌ 错误")
        self.status_label.setStyleSheet("color: #f85149; font-size: 12px; background: transparent;")
        self.send_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
    
    def clear_chat(self):
        # 清空所有消息
        while self.message_layout.count() > 1:
            item = self.message_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.history = []
        self.add_message("对话已清空。有什么可以帮你的吗？", is_user=False)


# ============================================================
# 任务页面
# ============================================================
class TasksPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tasks = []
        self.init_ui()
        self.load_tasks()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # 标题
        title = QLabel("📋 任务管理")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #e6edf3; background: transparent;")
        layout.addWidget(title)
        
        # 新建任务
        new_task_box = QGroupBox("新建任务")
        new_task_box.setStyleSheet("""
            QGroupBox {
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 8px;
                margin-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        new_task_layout = QVBoxLayout(new_task_box)
        
        self.task_input = QTextEdit()
        self.task_input.setPlaceholderText("描述你的任务...")
        self.task_input.setMaximumHeight(80)
        self.task_input.setStyleSheet("""
            QTextEdit {
                background: #0d1117;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        new_task_layout.addWidget(self.task_input)
        
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        add_btn = QPushButton("➕ 添加任务")
        add_btn.setStyleSheet("""
            QPushButton {
                background: #238636;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover { background: #2ea043; }
        """)
        add_btn.clicked.connect(self.add_task)
        btn_row.addWidget(add_btn)
        new_task_layout.addLayout(btn_row)
        layout.addWidget(new_task_box)
        
        # 任务列表
        list_box = QGroupBox("任务列表")
        list_box.setStyleSheet("""
            QGroupBox {
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 8px;
                margin-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        list_layout = QVBoxLayout(list_box)
        
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(5)
        self.task_table.setHorizontalHeaderLabels(["任务", "状态", "优先级", "创建时间", "操作"])
        self.task_table.horizontalHeader().setStretchLastSection(False)
        self.task_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.task_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.task_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.task_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.task_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.task_table.setColumnWidth(1, 80)
        self.task_table.setColumnWidth(2, 80)
        self.task_table.setColumnWidth(3, 140)
        self.task_table.setColumnWidth(4, 60)
        self.task_table.setStyleSheet("""
            QTableWidget {
                background: #0d1117;
                color: #e6edf3;
                border: none;
                gridline-color: #30363d;
            }
            QHeaderView::section {
                background: #161b22;
                color: #e6edf3;
                padding: 8px;
                border: 1px solid #30363d;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #30363d;
            }
            QTableWidget::item:selected {
                background: #1f6feb;
            }
        """)
        list_layout.addWidget(self.task_table)
        layout.addWidget(list_box)
        
        layout.addStretch()
    
    def add_task(self):
        text = self.task_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "提示", "请输入任务描述")
            return
        
        from datetime import datetime
        task = {
            "id": len(self.tasks) + 1,
            "text": text,
            "status": "待执行",
            "priority": "中",
            "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "result": None
        }
        self.tasks.append(task)
        self.task_input.clear()
        self.refresh_tasks()
        self.save_tasks()
        
        QMessageBox.information(self, "成功", "任务已添加")
    
    def refresh_tasks(self):
        self.task_table.setRowCount(len(self.tasks))
        for i, task in enumerate(self.tasks):
            self.task_table.setItem(i, 0, QTableWidgetItem(task["text"]))
            
            status_item = QTableWidgetItem(task["status"])
            if task["status"] == "已完成":
                status_item.setForeground(QColor("#3fb950"))
            elif task["status"] == "执行中":
                status_item.setForeground(QColor("#d29922"))
            self.task_table.setItem(i, 1, status_item)
            
            priority_item = QTableWidgetItem(task["priority"])
            if task["priority"] == "高":
                priority_item.setForeground(QColor("#f85149"))
            elif task["priority"] == "中":
                priority_item.setForeground(QColor("#d29922"))
            else:
                priority_item.setForeground(QColor("#3fb950"))
            self.task_table.setItem(i, 2, priority_item)
            
            self.task_table.setItem(i, 3, QTableWidgetItem(task["created"]))
            
            btn = QPushButton("🗑️")
            btn.setStyleSheet("background: transparent; border: none; font-size: 14px;")
            btn.setToolTip("删除任务")
            btn.clicked.connect(lambda checked, idx=i: self.delete_task(idx))
            self.task_table.setCellWidget(i, 4, btn)
    
    def delete_task(self, idx):
        if 0 <= idx < len(self.tasks):
            reply = QMessageBox.question(
                self, "确认", "确定要删除这个任务吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.tasks.pop(idx)
                self.refresh_tasks()
                self.save_tasks()
    
    def save_tasks(self):
        # 保存到文件
        try:
            import json
            tasks_file = Path(__file__).parent.parent / "data" / "tasks.json"
            tasks_file.parent.mkdir(parents=True, exist_ok=True)
            with open(tasks_file, "w", encoding="utf-8") as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存任务失败: {e}")
    
    def load_tasks(self):
        try:
            import json
            tasks_file = Path(__file__).parent.parent / "data" / "tasks.json"
            if tasks_file.exists():
                with open(tasks_file, "r", encoding="utf-8") as f:
                    self.tasks = json.load(f)
                self.refresh_tasks()
        except Exception as e:
            print(f"加载任务失败: {e}")


# ============================================================
# 统计页面
# ============================================================
class StatsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_stats()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        title = QLabel("📊 使用统计")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #e6edf3; background: transparent;")
        layout.addWidget(title)
        
        # 统计卡片
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)
        
        self.total_calls = self._create_card("总调用次数", "0", "🤖", "#58a6ff")
        self.total_tokens = self._create_card("总Token数", "0", "📝", "#a371f7")
        self.avg_time = self._create_card("平均响应", "0ms", "⏱️", "#3fb950")
        self.success_rate = self._create_card("成功率", "0%", "✅", "#238636")
        
        cards_layout.addWidget(self.total_calls)
        cards_layout.addWidget(self.total_tokens)
        cards_layout.addWidget(self.avg_time)
        cards_layout.addWidget(self.success_rate)
        layout.addLayout(cards_layout)
        
        # 详细统计
        detail_box = QGroupBox("详细统计")
        detail_box.setStyleSheet("""
            QGroupBox {
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 8px;
                margin-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        detail_layout = QVBoxLayout(detail_box)
        
        self.detail_label = QLabel("加载中...")
        self.detail_label.setStyleSheet("color: #8b949e; background: transparent; line-height: 1.8;")
        detail_layout.addWidget(self.detail_label)
        layout.addWidget(detail_box)
        
        # 刷新按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        refresh_btn = QPushButton("🔄 刷新统计")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: #1f6feb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover { background: #388bfd; }
        """)
        refresh_btn.clicked.connect(self.load_stats)
        btn_row.addWidget(refresh_btn)
        layout.addLayout(btn_row)
        
        layout.addStretch()
    
    def _create_card(self, title, value, icon, color):
        card = QFrame()
        card.setFrameShape(QFrame.Shape.Box)
        card.setStyleSheet(f"""
            QFrame {{
                background: #161b22;
                border: 1px solid #30363d;
                border-radius: 12px;
                padding: 16px;
            }}
        """)
        layout = QVBoxLayout(card)
        
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"font-size: 32px; background: transparent; color: {color};")
        layout.addWidget(icon_label)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #8b949e; font-size: 12px; background: transparent;")
        layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setObjectName(f"value_{title.replace(' ', '_')}")
        value_label.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: bold; background: transparent;")
        layout.addWidget(value_label)
        
        return card
    
    def load_stats(self):
        try:
            from app.utils.stats import get_stats
            stats = get_stats()
            
            # 更新卡片
            for card in [self.total_calls, self.total_tokens, self.avg_time, self.success_rate]:
                value_labels = [w for w in card.findChildren(QLabel) if w.objectName().startswith("value_")]
                if value_labels:
                    value_label = value_labels[0]
                    title = card.findChildren(QLabel)[1].text()
                    if title == "总调用次数":
                        value_label.setText(str(stats.total_model_calls))
                    elif title == "总Token数":
                        value_label.setText(str(stats.total_tokens))
                    elif title == "平均响应":
                        avg = stats.avg_response_time if stats.total_model_calls > 0 else 0
                        value_label.setText(f"{avg:.0f}ms")
                    elif title == "成功率":
                        rate = (stats.successful_tasks / stats.total_tasks * 100) if stats.total_tasks > 0 else 0
                        value_label.setText(f"{rate:.1f}%")
            
            # 更新详细信息
            detail_text = f"""总任务数: {stats.total_tasks}
成功任务: {stats.successful_tasks}
失败任务: {stats.total_tasks - stats.successful_tasks}
API调用次数: {stats.total_api_calls}
平均响应时间: {stats.avg_response_time:.2f}ms
"""
            self.detail_label.setText(detail_text)
            
        except Exception as e:
            self.detail_label.setText(f"加载统计失败: {e}\n\n请确保后端已正确配置。")


# ============================================================
# 设置页面
# ============================================================
class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        title = QLabel("⚙️ 设置")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #e6edf3; background: transparent;")
        layout.addWidget(title)
        
        # API设置
        api_box = QGroupBox("API 配置")
        api_box.setStyleSheet("""
            QGroupBox {
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 8px;
                margin-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        api_layout = QFormLayout(api_box)
        api_layout.setSpacing(12)
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("输入 NVIDIA API Key...")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setStyleSheet("""
            QLineEdit {
                background: #0d1117;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        api_layout.addRow("API Key:", self.api_key_input)
        
        self.base_url_input = QLineEdit()
        self.base_url_input.setText("https://integrate.api.nvidia.com/v1")
        self.base_url_input.setStyleSheet("""
            QLineEdit {
                background: #0d1117;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        api_layout.addRow("Base URL:", self.base_url_input)
        
        self.show_key_check = QCheckBox("显示 API Key")
        self.show_key_check.setStyleSheet("color: #c9d1d9; background: transparent;")
        self.show_key_check.stateChanged.connect(self.toggle_key_visibility)
        api_layout.addRow(self.show_key_check)
        
        save_btn = QPushButton("💾 保存配置")
        save_btn.setStyleSheet("""
            QPushButton {
                background: #238636;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover { background: #2ea043; }
        """)
        save_btn.clicked.connect(self.save_settings)
        api_layout.addRow(save_btn)
        layout.addWidget(api_box)
        
        # 关于
        about_box = QGroupBox("关于 Agent Studio")
        about_box.setStyleSheet("""
            QGroupBox {
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 8px;
                margin-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        about_layout = QVBoxLayout(about_box)
        about_text = QLabel("""
Agent Studio v1.0
基于 PyQt6 开发的智能体桌面应用

功能特性:
• 多模型支持 (NVIDIA NIM, OpenAI, Claude)
• 多种执行模式 (简单问答、ReAct、多Agent协作)
• 任务管理系统
• 使用统计分析
• 知识库检索 (RAG)

技术栈:
• PyQt6 桌面框架
• LangGraph + LangChain
• ChromaDB 向量数据库
        """)
        about_text.setStyleSheet("color: #8b949e; background: transparent; line-height: 1.6;")
        about_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_layout.addWidget(about_text)
        layout.addWidget(about_box)
        
        layout.addStretch()
    
    def toggle_key_visibility(self, state):
        if state == Qt.CheckState.Checked.value:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
    
    def save_settings(self):
        api_key = self.api_key_input.text()
        base_url = self.base_url_input.text()
        
        env_path = Path(__file__).parent.parent / ".env"
        try:
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(f"NVIDIA_API_KEY={api_key}\n")
                f.write(f"NVIDIA_BASE_URL={base_url}\n")
            QMessageBox.information(self, "成功", "配置已保存！\n重启应用后生效。")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {e}")
    
    def load_settings(self):
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("NVIDIA_API_KEY="):
                            self.api_key_input.setText(line.strip().split("=", 1)[1])
                        elif line.startswith("NVIDIA_BASE_URL="):
                            self.base_url_input.setText(line.strip().split("=", 1)[1])
            except Exception as e:
                print(f"加载设置失败: {e}")


# ============================================================
# 侧边栏
# ============================================================
class SideBar(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(64)
        self.setSpacing(6)
        self.setStyleSheet("""
            QListWidget {
                background: #010409;
                border: none;
                padding: 12px 4px;
            }
            QListWidget::item {
                padding: 12px 0;
                border-radius: 8px;
                color: #484f58;
                font-size: 24px;
                text-align: center;
            }
            QListWidget::item:selected {
                background: #161b22;
                color: #58a6ff;
                border: 1px solid #30363d;
            }
            QListWidget::item:hover:!selected {
                background: #0d1117;
                color: #8b949e;
            }
        """)


# ============================================================
# 主窗口
# ============================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Agent Studio - 智能体工作室")
        self.setGeometry(80, 80, 1280, 850)
        self.setMinimumSize(800, 600)
        
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        
        self.sidebar = SideBar()
        items = [
            ("💬", "聊天"),
            ("📋", "任务"),
            ("📊", "统计"),
            ("⚙️", "设置")
        ]
        for icon, tooltip in items:
            item = QListWidgetItem(icon)
            item.setSizeHint(QSize(56, 50))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setToolTip(tooltip)
            self.sidebar.addItem(item)
        self.sidebar.setCurrentRow(0)
        root.addWidget(self.sidebar)
        
        self.stack = QStackedWidget()
        self.chat_page = ChatPage()
        self.tasks_page = TasksPage()
        self.stats_page = StatsPage()
        self.settings_page = SettingsPage()
        
        self.stack.addWidget(self.chat_page)
        self.stack.addWidget(self.tasks_page)
        self.stack.addWidget(self.stats_page)
        self.stack.addWidget(self.settings_page)
        
        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)
        root.addWidget(self.stack, stretch=1)
        
        self.setStyleSheet("""
            QMainWindow { background: #0d1117; }
            QWidget { background: #0d1117; color: #e6edf3; }
            QLabel { background: transparent; }
            QScrollBar:vertical {
                background: #0d1117;
                width: 8px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: #30363d;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover { background: #484f58; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar:horizontal {
                background: #0d1117;
                height: 8px;
                border: none;
            }
            QScrollBar::handle:horizontal {
                background: #30363d;
                border-radius: 4px;
                min-width: 20px;
            }
        """)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#0d1117"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#e6edf3"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#0d1117"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#161b22"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#e6edf3"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#21262d"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#e6edf3"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#1f6feb"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)
    
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
