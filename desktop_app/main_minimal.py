#!/usr/bin/env python3
"""
Agent Studio - 最简版（直接调 NVIDIA API）
"""
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

import os
from pathlib import Path


class ApiWorker(QThread):
    result_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, message, api_key):
        super().__init__()
        self.message = message
        self.api_key = api_key
    
    def run(self):
        try:
            from openai import OpenAI
            
            client = OpenAI(
                api_key=self.api_key,
                base_url="https://integrate.api.nvidia.com/v1"
            )
            
            response = client.chat.completions.create(
                model="deepseek-ai/deepseek-v4-flash",
                messages=[{"role": "user", "content": self.message}],
                temperature=0.7,
                max_tokens=2000
            )
            
            answer = response.choices[0].message.content
            self.result_ready.emit(answer)
            
        except Exception as e:
            self.error_occurred.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.api_key = ""
        self.load_key()
        self.init_ui()
    
    def load_key(self):
        # 从 .env 读取
        env_file = Path(".env")
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("NVIDIA_API_KEY="):
                    self.api_key = line.split("=", 1)[1].strip()
                    break
        
        # 从用户目录读取
        if not self.api_key:
            user_env = Path.home() / ".agent_studio" / "settings.env"
            if user_env.exists():
                for line in user_env.read_text().splitlines():
                    if line.startswith("NVIDIA_API_KEY="):
                        self.api_key = line.split("=", 1)[1].strip()
                        break
    
    def init_ui(self):
        self.setWindowTitle("Agent Studio")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("background: #0d1117; color: #e6edf3;")
        
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # 状态栏
        self.status = QLabel("就绪" if self.api_key else "⚠️ 未配置 API Key")
        self.status.setStyleSheet("color: #3fb950; font-size: 12px; padding: 4px;")
        if not self.api_key:
            self.status.setStyleSheet("color: #d29922; font-size: 12px; padding: 4px;")
        layout.addWidget(self.status)
        
        # 消息区域
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setStyleSheet("""
            QTextEdit {
                background: #161b22;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.output, stretch=1)
        
        # 输入区域
        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)
        
        self.input = QTextEdit()
        self.input.setPlaceholderText("输入消息...")
        self.input.setMaximumHeight(80)
        self.input.setStyleSheet("""
            QTextEdit {
                background: #0d1117;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
            }
        """)
        input_layout.addWidget(self.input, stretch=1)
        
        self.send_btn = QPushButton("发送")
        self.send_btn.setFixedSize(80, 80)
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
        self.send_btn.clicked.connect(self.send)
        input_layout.addWidget(self.send_btn)
        
        layout.addLayout(input_layout)
    
    def send(self):
        text = self.input.toPlainText().strip()
        if not text:
            return
        
        if not self.api_key:
            self.status.setText("错误: 请先配置 API Key (编辑 .env 文件)")
            return
        
        self.output.append(f"<b>我:</b> {text}<br>")
        self.input.clear()
        self.send_btn.setEnabled(False)
        self.status.setText("处理中...")
        self.status.setStyleSheet("color: #d29922; font-size: 12px;")
        
        self.worker = ApiWorker(text, self.api_key)
        self.worker.result_ready.connect(self.on_result)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.start()
    
    def on_result(self, answer):
        self.output.append(f"<b>智能体:</b> {answer}<br>")
        self.send_btn.setEnabled(True)
        self.status.setText("就绪")
        self.status.setStyleSheet("color: #3fb950; font-size: 12px;")
    
    def on_error(self, error):
        self.output.append(f"<span style='color: #f85149;'>错误: {error}</span><br>")
        self.send_btn.setEnabled(True)
        self.status.setText("错误")
        self.status.setStyleSheet("color: #f85149; font-size: 12px;")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
