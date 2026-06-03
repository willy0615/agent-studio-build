import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QComboBox, QLineEdit,
    QFrame, QScrollArea, QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor

import os
from pathlib import Path


# ============================================================
# 消息气泡
# ============================================================
class MessageBubble(QFrame):
    def __init__(self, text, is_user=True, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        bubble = QFrame()
        bubble.setFrameShape(QFrame.Shape.Box)
        bubble.setLineWidth(0)
        
        if is_user:
            bubble.setStyleSheet("""
                QFrame {
                    background-color: #1f4d7a;
                    border: 1px solid #2d5a8a;
                    border-radius: 12px;
                }
            """)
            layout.addStretch(3)
        else:
            bubble.setStyleSheet("""
                QFrame {
                    background-color: #21262d;
                    border: 1px solid #30363d;
                    border-radius: 12px;
                }
            """)
            layout.addStretch(1)
        
        bl = QVBoxLayout(bubble)
        bl.setContentsMargins(12, 10, 12, 10)
        
        msg = QLabel(text)
        msg.setWordWrap(True)
        msg.setStyleSheet("color: #e1e4e8; font-size: 14px; background: transparent; line-height: 1.5;")
        bl.addWidget(msg)
        
        layout.addWidget(bubble)
        
        if is_user:
            layout.addStretch(1)
        else:
            layout.addStretch(3)


# ============================================================
# API 工作线程
# ============================================================
class ApiWorker(QThread):
    result_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    progress_update = pyqtSignal(str)
    
    def __init__(self, message, api_key, base_url, model):
        super().__init__()
        self.message = message
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
    
    def run(self):
        try:
            from openai import OpenAI
            
            self.progress_update.emit("正在连接 API...")
            
            client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            
            self.progress_update.emit(f"正在调用模型: {self.model}...")
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": self.message}],
                temperature=0.7,
                max_tokens=2000
            )
            
            answer = response.choices[0].message.content
            self.result_ready.emit(answer)
            
        except Exception as e:
            self.error_occurred.emit(str(e))


# ============================================================
# 主窗口
# ============================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.api_key = ""
        self.base_url = "https://integrate.api.nvidia.com/v1"
        self.model = "deepseek-ai/deepseek-v4-flash"
        self.history = []
        self.init_ui()
        self.load_config()
    
    def init_ui(self):
        self.setWindowTitle("Agent Studio - 智能体工作室")
        self.setGeometry(100, 100, 1000, 700)
        self.setStyleSheet("QMainWindow { background: #0d1117; }")
        
        # 中央部件
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 顶部工具栏
        top_bar = QFrame()
        top_bar.setFrameShape(QFrame.Shape.NoFrame)
        top_bar.setFixedHeight(50)
        top_bar.setStyleSheet("QFrame { background: #161b22; border-bottom: 1px solid #30363d; }")
        
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(16, 0, 16, 0)
        top_layout.setSpacing(12)
        
        # 模型选择
        model_label = QLabel("模型:")
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
        
        top_layout.addStretch()
        
        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #3fb950; font-size: 12px; background: transparent; padding: 4px 12px;")
        top_layout.addWidget(self.status_label)
        
        main_layout.addWidget(top_bar)
        
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
        main_layout.addWidget(self.scroll, stretch=1)
        
        # 输入区域
        input_frame = QFrame()
        input_frame.setFrameShape(QFrame.Shape.NoFrame)
        input_frame.setStyleSheet("QFrame { background: #161b22; border-top: 1px solid #30363d; }")
        
        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(16, 12, 16, 12)
        input_layout.setSpacing(8)
        
        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("输入消息，按 Ctrl+Enter 发送...")
        self.input_field.setMaximumHeight(100)
        self.input_field.setStyleSheet("""
            QTextEdit {
                background: #0d1117;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 10px 12px;
                font-size: 14px;
            }
            QTextEdit:focus {
                border: 1px solid #388bfd;
            }
        """)
        input_layout.addWidget(self.input_field)
        
        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        
        btn_row.addStretch()
        
        self.send_btn = QPushButton("发送")
        self.send_btn.setFixedSize(80, 36)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background: #238636;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background: #2ea043; }
            QPushButton:disabled { background: #30363d; }
        """)
        self.send_btn.clicked.connect(self.send_message)
        btn_row.addWidget(self.send_btn)
        
        input_layout.addLayout(btn_row)
        
        main_layout.addWidget(input_frame)
        
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
        self.model = text
    
    def send_message(self):
        text = self.input_field.toPlainText().strip()
        if not text:
            return
        
        if not self.api_key:
            self.status_label.setText("错误: 请先配置 API Key")
            self.status_label.setStyleSheet("color: #f85149; font-size: 12px;")
            return
        
        # 添加用户消息
        self.add_message(text, is_user=True)
        self.input_field.clear()
        
        # 禁用按钮
        self.send_btn.setEnabled(False)
        self.status_label.setText("处理中...")
        self.status_label.setStyleSheet("color: #d29922; font-size: 12px;")
        
        # 调用 API
        self.worker = ApiWorker(text, self.api_key, self.base_url, self.model)
        self.worker.result_ready.connect(self.on_result)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.progress_update.connect(self.on_progress)
        self.worker.start()
    
    def add_message(self, text, is_user=True):
        bubble = MessageBubble(text, is_user=is_user)
        self.message_layout.insertWidget(self.message_layout.count() - 1, bubble)
    
    def on_result(self, answer):
        self.add_message(answer, is_user=False)
        self.send_btn.setEnabled(True)
        self.status_label.setText("就绪")
        self.status_label.setStyleSheet("color: #3fb950; font-size: 12px;")
    
    def on_error(self, error_msg):
        self.status_label.setText(f"错误: {error_msg[:50]}")
        self.status_label.setStyleSheet("color: #f85149; font-size: 12px;")
        self.send_btn.setEnabled(True)
    
    def on_progress(self, text):
        self.status_label.setText(text)
        self.status_label.setStyleSheet("color: #d29922; font-size: 12px;")
    
    def load_config(self):
        # 从 .env 加载
        env_file = Path(".env")
        if env_file.exists():
            from dotenv import load_dotenv
            load_dotenv()
        
        self.api_key = os.getenv("NVIDIA_API_KEY", "")
        self.base_url = os.getenv("NVIDIA_BASE_URL", self.base_url)
        
        # 从用户配置加载
        user_config = Path.home() / ".agent_studio" / "settings.env"
        if user_config.exists():
            from dotenv import load_dotenv
            load_dotenv(user_config)
            self.api_key = os.getenv("NVIDIA_API_KEY", self.api_key)
            self.base_url = os.getenv("NVIDIA_BASE_URL", self.base_url)
        
        if self.api_key:
            self.status_label.setText("API Key 已配置")
            self.status_label.setStyleSheet("color: #3fb950; font-size: 12px;")
        else:
            self.status_label.setText("警告: 未配置 API Key")
            self.status_label.setStyleSheet("color: #d29922; font-size: 12px;")


# ============================================================
# 主函数
# ============================================================
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # 设置应用样式
    app.setPalette(QPalette(QColor("#0d1117")))
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
