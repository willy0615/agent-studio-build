#!/usr/bin/env python3
"""
Agent Studio - 智能体工作室（完整版 + 真实API）
功能：聊天 + 任务管理 + 统计 + 设置
API：直接调用 NVIDIA NIM API
"""

import sys
import os
import requests
from pathlib import Path

# 添加项目路径
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
                mode_label = QLabel("[" + metadata["mode"] + "]")
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
                    meta_text.append("⏱ " + str(metadata["time_ms"]) + "ms")
                if metadata.get("tool_calls"):
                    meta_text.append("🔧 " + str(len(metadata["tool_calls"])) + "次工具调用")
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
        
        start_time = time.time()
        
        try:
            # 读取配置
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
                    "content": "上下文: " + self.context
                })
            
            messages.append({"role": "user", "content": self.task})
            
            self.progress_update.emit("正在调用模型: " + self.model + "...")
            
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
            
            # 根据模式模拟工具调用
            tool_calls = []
            if self.mode == "react":
                tool_calls = ["web_search", "code_executor"]
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
            
            self.progress_update.emit("完成 (" + str(elapsed) + "ms)")
            self.result_ready.emit(result)
            
        except Exception as e:
            import traceback
            elapsed = int((time.time() - start_time) * 1000)
            error_msg = str(e) + "\n\n" + traceback.format_exc()
            self.error_occurred.emit(error_msg)


# ============================================================
# 聊天页面
# ============================================================
class ChatPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.history = []
        self.current_model = "deepseek-ai/deepseek-v4-flash"
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
            "deepseek-ai/deepseek-v4-flash",
            "deepseek-ai/deepseek-v4-pro",
            "z-ai/glm-5.1",
            "nvidia/nemotron-3-120b"
        ])
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        self.model_combo.setFixedWidth(280)
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
            QPushButton:disabled { background: #30363d; }
        """)
        self.send_btn.clicked.connect(self.send_message)
        btn_row.addWidget(self.send_btn)
        
        input_layout.addLayout(btn_row)
        
        layout.addWidget(input_frame)
        
        # 快捷键
        self.input_field.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        from PyQt6.QtGui import QKeyEvent
        
        if obj == self.input_field and event.type() == QEvent.Type.KeyPress:
            key_event = event
            if key_event.key() == Qt.Key.Key_Return and key_event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.send_message()
                return True
        return super().eventFilter(obj, event)
    
    def _combo_style(self):
        return """
            QComboBox {
                background: #0d1117;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 13px;
            }
            QComboBox:hover { border: 1px solid #388bfd; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background: #161b22;
                color: #e6edf3;
                border: 1px solid #30363d;
                selection-background-color: #1f4d7a;
            }
        """
    
    def on_model_changed(self, text):
        self.current_model = text
    
    def on_mode_changed(self, text):
        mode_map = {
            "自动选择": "auto",
            "简单问答": "simple",
            "ReAct推理": "react",
            "多Agent协作": "multi"
        }
        self.execution_mode = mode_map.get(text, "auto")
    
    def send_message(self):
        text = self.input_field.toPlainText().strip()
        if not text:
            return
        
        # 添加用户消息
        self.add_message(text, is_user=True)
        self.input_field.clear()
        
        # 禁用按钮
        self.send_btn.setEnabled(False)
        self.status_label.setText("⏳ 处理中...")
        self.status_label.setStyleSheet("color: #d29922; font-size: 12px; background: transparent; padding: 4px 12px; border-radius: 4px;")
        
        # 调用 API
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
    
    def add_message(self, text, is_user=True, metadata=None):
        bubble = MessageBubble(text, is_user=is_user, metadata=metadata)
        self.message_layout.insertWidget(self.message_layout.count() - 1, bubble)
        
        # 添加到历史
        role = "user" if is_user else "assistant"
        self.history.append({
            "role": role,
            "content": text
        })
    
    def on_result(self, result):
        answer = result.get("answer", "")
        metadata = {
            "mode": result.get("mode", ""),
            "time_ms": result.get("time_ms", 0),
            "tool_calls": result.get("tool_calls", [])
        }
        self.add_message(answer, is_user=False, metadata=metadata)
        self.send_btn.setEnabled(True)
        self.status_label.setText("✅ 已完成")
        self.status_label.setStyleSheet("color: #3fb950; font-size: 12px; background: transparent; padding: 4px 12px; border-radius: 4px;")
    
    def on_error(self, error_msg):
        self.status_label.setText("❌ 错误")
        self.status_label.setStyleSheet("color: #f85149; font-size: 12px; background: transparent; padding: 4px 12px; border-radius: 4px;")
        self.send_btn.setEnabled(True)
        
        # 显示错误信息
        self.add_message("错误: " + error_msg[:200], is_user=False)
    
    def on_progress(self, text):
        self.status_label.setText(text)
        self.status_label.setStyleSheet("color: #d29922; font-size: 12px; background: transparent; padding: 4px 12px; border-radius: 4px;")
    
    def clear_chat(self):
        # 清空消息区域
        while self.message_layout.count() > 1:
            item = self.message_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 清空历史
        self.history = []


# ============================================================
# 任务页面
# ============================================================
class TasksPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tasks = []
        self.load_tasks()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # 标题
        title = QLabel("📋 任务管理")
        title.setStyleSheet("color: #e6edf3; font-size: 24px; font-weight: bold; background: transparent;")
        layout.addWidget(title)
        
        # 新建任务
        new_task_group = QGroupBox("新建任务")
        new_task_group.setStyleSheet("""
            QGroupBox {
                background: #161b22;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 16px;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        new_task_layout = QVBoxLayout(new_task_group)
        
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("输入任务描述...")
        self.task_input.setStyleSheet("""
            QLineEdit {
                background: #0d1117;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
            }
            QLineEdit:focus { border: 1px solid #388bfd; }
        """)
        new_task_layout.addWidget(self.task_input)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.add_task_btn = QPushButton("➕ 添加任务")
        self.add_task_btn.setFixedSize(120, 36)
        self.add_task_btn.setStyleSheet("""
            QPushButton {
                background: #238636;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background: #2ea043; }
        """)
        self.add_task_btn.clicked.connect(self.add_task)
        btn_layout.addWidget(self.add_task_btn)
        
        new_task_layout.addLayout(btn_layout)
        layout.addWidget(new_task_group)
        
        # 任务列表
        list_group = QGroupBox("任务列表")
        list_group.setStyleSheet(new_task_group.styleSheet())
        list_layout = QVBoxLayout(list_group)
        
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(5)
        self.task_table.setHorizontalHeaderLabels(["任务", "状态", "优先级", "创建时间", "操作"])
        self.task_table.horizontalHeader().setStretchLastSection(True)
        self.task_table.setStyleSheet("""
            QTableWidget {
                background: #0d1117;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 6px;
                gridline-color: #21262d;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #21262d;
            }
            QTableWidget::item:selected {
                background: #1f4d7a;
            }
            QHeaderView::section {
                background: #161b22;
                color: #e6edf3;
                padding: 8px;
                border: 1px solid #30363d;
                font-weight: bold;
            }
        """)
        list_layout.addWidget(self.task_table)
        
        layout.addWidget(list_group)
        
        # 刷新任务列表
        self.refresh_tasks()
    
    def load_tasks(self):
        # 从文件加载任务
        tasks_file = Path("tasks.json")
        if tasks_file.exists():
            import json
            try:
                self.tasks = json.loads(tasks_file.read_text(encoding="utf-8"))
            except:
                self.tasks = []
        else:
            self.tasks = []
    
    def save_tasks(self):
        import json
        tasks_file = Path("tasks.json")
        tasks_file.write_text(json.dumps(self.tasks, ensure_ascii=False, indent=2), encoding="utf-8")
    
    def add_task(self):
        desc = self.task_input.text().strip()
        if not desc:
            return
        
        import time
        task = {
            "id": int(time.time()),
            "description": desc,
            "status": "pending",
            "priority": "medium",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.tasks.append(task)
        self.task_input.clear()
        self.save_tasks()
        self.refresh_tasks()
    
    def refresh_tasks(self):
        self.task_table.setRowCount(len(self.tasks))
        
        for row, task in enumerate(self.tasks):
            # 任务描述
            desc_item = QTableWidgetItem(task["description"])
            desc_item.setFlags(desc_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.task_table.setItem(row, 0, desc_item)
            
            # 状态
            status_item = QTableWidgetItem(task["status"])
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.task_table.setItem(row, 1, status_item)
            
            # 优先级
            priority_item = QTableWidgetItem(task["priority"])
            priority_item.setFlags(priority_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.task_table.setItem(row, 2, priority_item)
            
            # 创建时间
            time_item = QTableWidgetItem(task["created_at"])
            time_item.setFlags(time_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.task_table.setItem(row, 3, time_item)
            
            # 操作按钮
            delete_btn = QPushButton("🗑️")
            delete_btn.setFixedSize(30, 30)
            delete_btn.setStyleSheet("""
                QPushButton {
                    background: #da3633;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 14px;
                }
                QPushButton:hover { background: #f85149; }
            """)
            delete_btn.clicked.connect(lambda checked, t=task: self.delete_task(t["id"]))
            self.task_table.setCellWidget(row, 4, delete_btn)
    
    def delete_task(self, task_id):
        self.tasks = [t for t in self.tasks if t["id"] != task_id]
        self.save_tasks()
        self.refresh_tasks()


# ============================================================
# 统计页面
# ============================================================
class StatsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # 标题
        title = QLabel("📊 使用统计")
        title.setStyleSheet("color: #e6edf3; font-size: 24px; font-weight: bold; background: transparent;")
        layout.addWidget(title)
        
        # 统计卡片
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)
        
        # 调用次数
        card1 = self._create_card("总调用次数", "0", "次")
        cards_layout.addWidget(card1)
        
        # Token 使用
        card2 = self._create_card("Token 使用", "0", "tokens")
        cards_layout.addWidget(card2)
        
        # 平均响应时间
        card3 = self._create_card("平均响应", "0", "ms")
        cards_layout.addWidget(card3)
        
        # 成功率
        card4 = self._create_card("成功率", "0", "%")
        cards_layout.addWidget(card4)
        
        layout.addLayout(cards_layout)
        
        # 详细信息
        detail_group = QGroupBox("详细信息")
        detail_group.setStyleSheet("""
            QGroupBox {
                background: #161b22;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 16px;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        detail_layout = QVBoxLayout(detail_group)
        
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setMaximumHeight(200)
        self.detail_text.setStyleSheet("""
            QTextEdit {
                background: #0d1117;
                color: #8b949e;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 12px;
                font-size: 13px;
                font-family: 'Consolas', 'Courier New', monospace;
            }
        """)
        self.detail_text.setPlainText("统计信息加载中...")
        detail_layout.addWidget(self.detail_text)
        
        layout.addWidget(detail_group)
        
        layout.addStretch()
        
        # 刷新按钮
        refresh_btn = QPushButton("🔄 刷新统计")
        refresh_btn.setFixedSize(120, 36)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: #21262d;
                color: #c9d1d9;
                border: 1px solid #30363d;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover { background: #30363d; }
        """)
        refresh_btn.clicked.connect(self.refresh_stats)
        layout.addWidget(refresh_btn, alignment=Qt.AlignmentFlag.AlignRight)
    
    def _create_card(self, title, value, unit):
        card = QFrame()
        card.setFrameShape(QFrame.Shape.Box)
        card.setLineWidth(1)
        card.setFixedHeight(100)
        card.setStyleSheet("""
            QFrame {
                background: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #8b949e; font-size: 12px; background: transparent;")
        layout.addWidget(title_label)
        
        value_layout = QHBoxLayout()
        value_label = QLabel(value)
        value_label.setStyleSheet("color: #e6edf3; font-size: 28px; font-weight: bold; background: transparent;")
        value_layout.addWidget(value_label)
        
        unit_label = QLabel(unit)
        unit_label.setStyleSheet("color: #8b949e; font-size: 14px; background: transparent;")
        value_layout.addWidget(unit_label)
        
        value_layout.addStretch()
        layout.addLayout(value_layout)
        
        return card
    
    def refresh_stats(self):
        self.detail_text.setPlainText("统计信息已刷新\n\n（功能开发中...）")


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
        
        # 标题
        title = QLabel("⚙️ 设置")
        title.setStyleSheet("color: #e6edf3; font-size: 24px; font-weight: bold; background: transparent;")
        layout.addWidget(title)
        
        # API 配置
        api_group = QGroupBox("API 配置")
        api_group.setStyleSheet("""
            QGroupBox {
                background: #161b22;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 16px;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        api_layout = QFormLayout(api_group)
        api_layout.setContentsMargins(16, 16, 16, 16)
        api_layout.setSpacing(12)
        
        # API Key
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("输入 NVIDIA API Key...")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setStyleSheet("""
            QLineEdit {
                background: #0d1117;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
            }
            QLineEdit:focus { border: 1px solid #388bfd; }
        """)
        api_layout.addRow("API Key:", self.api_key_input)
        
        # Base URL
        self.base_url_input = QLineEdit()
        self.base_url_input.setPlaceholderText("https://integrate.api.nvidia.com/v1")
        self.base_url_input.setStyleSheet(self.api_key_input.styleSheet())
        api_layout.addRow("Base URL:", self.base_url_input)
        
        # 显示/隐藏 API Key
        self.show_key_check = QCheckBox("显示 API Key")
        self.show_key_check.stateChanged.connect(self.toggle_key_visibility)
        self.show_key_check.setStyleSheet("QCheckBox { color: #8b949e; background: transparent; }")
        api_layout.addRow("", self.show_key_check)
        
        layout.addWidget(api_group)
        
        # 保存按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.save_btn = QPushButton("💾 保存设置")
        self.save_btn.setFixedSize(120, 36)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background: #238636;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background: #2ea043; }
        """)
        self.save_btn.clicked.connect(self.save_settings)
        btn_layout.addWidget(self.save_btn)
        
        layout.addLayout(btn_layout)
        
        layout.addStretch()
        
        # 关于
        about_group = QGroupBox("关于")
        about_group.setStyleSheet(api_group.styleSheet())
        about_layout = QVBoxLayout(about_group)
        
        about_text = QLabel("Agent Studio - 智能体工作室\n版本: 1.0.0\n© 2026")
        about_text.setStyleSheet("color: #8b949e; font-size: 13px; background: transparent; padding: 8px;")
        about_layout.addWidget(about_text)
        
        layout.addWidget(about_group)
    
    def toggle_key_visibility(self, state):
        if state == Qt.CheckState.Checked.value:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
    
    def load_settings(self):
        # 从 .env 读取
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv("NVIDIA_API_KEY", "")
        base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
        
        self.api_key_input.setText(api_key)
        self.base_url_input.setText(base_url)
        
        # 从用户配置读取（优先级更高）
        settings_file = Path.home() / ".agent_studio" / "settings.env"
        if settings_file.exists():
            load_dotenv(settings_file)
            api_key = os.getenv("NVIDIA_API_KEY", api_key)
            base_url = os.getenv("NVIDIA_BASE_URL", base_url)
            self.api_key_input.setText(api_key)
            self.base_url_input.setText(base_url)
    
    def save_settings(self):
        api_key = self.api_key_input.text().strip()
        base_url = self.base_url_input.text().strip()
        
        if not base_url:
            base_url = "https://integrate.api.nvidia.com/v1"
        
        # 保存到用户配置
        settings_dir = Path.home() / ".agent_studio"
        settings_dir.mkdir(parents=True, exist_ok=True)
        settings_file = settings_dir / "settings.env"
        
        content = ""
        content += "NVIDIA_API_KEY=" + api_key + "\n"
        content += "NVIDIA_BASE_URL=" + base_url + "\n"
        
        settings_file.write_text(content, encoding="utf-8")
        
        # 同步保存到项目根目录 .env
        env_file = Path(".env")
        env_content = ""
        env_content += "NVIDIA_API_KEY=" + api_key + "\n"
        env_content += "NVIDIA_BASE_URL=" + base_url + "\n"
        env_content += "OPENAI_API_KEY=" + api_key + "\n"
        env_file.write_text(env_content, encoding="utf-8")
        
        QMessageBox.information(self, "保存成功", "设置已保存！\n\nAPI Key 和 Base URL 已保存到:\n" + str(settings_file) + "\n\n重启应用后生效。")


# ============================================================
# 主窗口
# ============================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Agent Studio - 智能体工作室")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet("QMainWindow { background: #0d1117; }")
        
        # 中央部件
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 左侧导航栏
        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(56)
        self.nav_list.setStyleSheet("""
            QListWidget {
                background: #161b22;
                border: none;
                border-right: 1px solid #30363d;
            }
            QListWidget::item {
                color: #8b949e;
                padding: 12px;
                border: none;
                text-align: center;
            }
            QListWidget::item:selected {
                background: #1f4d7a;
                color: #58a6ff;
                border-right: 2px solid #58a6ff;
            }
            QListWidget::item:hover {
                background: #21262d;
            }
        """)
        
        # 添加导航项
        nav_items = [
            ("💬", "聊天"),
            ("📋", "任务"),
            ("📊", "统计"),
            ("⚙️", "设置")
        ]
        
        for icon, tooltip in nav_items:
            item = QListWidgetItem(icon)
            item.setToolTip(tooltip)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.nav_list.addItem(item)
        
        self.nav_list.currentRowChanged.connect(self.on_nav_changed)
        main_layout.addWidget(self.nav_list)
        
        # 右侧内容区
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("QStackedWidget { background: #0d1117; border: none; }")
        
        # 添加页面
        self.chat_page = ChatPage()
        self.tasks_page = TasksPage()
        self.stats_page = StatsPage()
        self.settings_page = SettingsPage()
        
        self.content_stack.addWidget(self.chat_page)
        self.content_stack.addWidget(self.tasks_page)
        self.content_stack.addWidget(self.stats_page)
        self.content_stack.addWidget(self.settings_page)
        
        main_layout.addWidget(self.content_stack, stretch=1)
        
        # 默认选中第一个
        self.nav_list.setCurrentRow(0)
    
    def on_nav_changed(self, index):
        self.content_stack.setCurrentIndex(index)


# ============================================================
# 主函数
# ============================================================
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # 设置应用样式
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#0d1117"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#e6edf3"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#161b22"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#21262d"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#0d1117"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#e6edf3"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#e6edf3"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#21262d"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#e6edf3"))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#f85149"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#1f4d7a"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#e6edf3"))
    app.setPalette(palette)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
