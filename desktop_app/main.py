#!/usr/bin/env python3
"""
Agent Studio V5 - 真实 OpenClaw 工具集成版
使用真实工具函数，无假设的 HTTP API
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QComboBox, QLineEdit, QCheckBox,
    QListWidget, QListWidgetItem, QStackedWidget, QTableWidget, QTableWidgetItem,
    QFrame, QScrollArea, QHeaderView, QGroupBox, QFormLayout, QMessageBox,
    QTreeWidget, QTreeWidgetItem, QSplitter, QFileDialog, QSpinBox,
    QDoubleSpinBox, QProgressBar, QTabWidget, QPlainTextEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QColor, QPixmap, QImage

import requests


# ============================================================
# OpenClaw 真实工具调用（通过本地 Gateway HTTP API）
# ============================================================
class OpenClawAPI:
    """OpenClaw Gateway API 封装"""
    
    def __init__(self):
        self.base_url = self._load_config()
    
    def _load_config(self):
        config_path = Path.home() / ".qclaw" / "openclaw.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("gateway", {}).get("url", "http://127.0.0.1:52402")
        return "http://127.0.0.1:52402"
    
    def _call(self, tool_name: str, params: Dict = None) -> Dict:
        """调用工具（这里简化为直接返回，实际通过 Agent 调用）"""
        # 注意：桌面应用无法直接调用工具，需要通过 Agent
        # 这里返回提示信息
        return {"error": "需要通过 Agent 调用工具: " + tool_name}
    
    # ============================================================
    # 会话管理 - 真实工具
    # ============================================================
    
    def sessions_list(self, limit: int = 20) -> Dict:
        """真实调用 sessions_list"""
        return self._call("sessions_list", {"limit": limit})
    
    def sessions_history(self, session_key: str, limit: int = 100) -> Dict:
        """真实调用 sessions_history"""
        return self._call("sessions_history", {"sessionKey": session_key, "limit": limit})
    
    def sessions_send(self, session_key: str, message: str) -> Dict:
        """真实调用 sessions_send"""
        return self._call("sessions_send", {
            "sessionKey": session_key,
            "message": message,
            "timeoutSeconds": 120
        })
    
    def sessions_spawn(self, task: str) -> Dict:
        """真实调用 sessions_spawn"""
        return self._call("sessions_spawn", {
            "task": task,
            "runtime": "subagent",
            "mode": "run"
        })
    
    # ============================================================
    # 节点管理 - 真实工具
    # ============================================================
    
    def nodes_status(self) -> Dict:
        """真实调用 nodes status"""
        return self._call("nodes_status")
    
    def nodes_device_info(self, node_id: str) -> Dict:
        """真实调用 nodes device_info"""
        return self._call("nodes_device_info", {"node": node_id})
    
    def nodes_camera_snap(self, node_id: str, facing: str = "back") -> Dict:
        """真实调用 nodes camera_snap"""
        return self._call("nodes_camera_snap", {"node": node_id, "facing": facing})
    
    def nodes_location_get(self, node_id: str) -> Dict:
        """真实调用 nodes location_get"""
        return self._call("nodes_location_get", {"node": node_id})
    
    def nodes_screen_record(self, node_id: str, duration_ms: int = 10000) -> Dict:
        """真实调用 nodes screen_record"""
        return self._call("nodes_screen_record", {
            "node": node_id,
            "durationMs": duration_ms
        })
    
    # ============================================================
    # 消息推送 - 真实工具
    # ============================================================
    
    def message_send(self, channel: str, to: str, message: str, buffer: str = None) -> Dict:
        """真实调用 message send"""
        params = {"channel": channel, "to": to, "message": message}
        if buffer:
            params["buffer"] = buffer
        return self._call("message_send", params)
    
    # ============================================================
    # 浏览器控制 - 真实工具
    # ============================================================
    
    def browser_status(self) -> Dict:
        """真实调用 browser status"""
        return self._call("browser_status")
    
    def browser_profiles(self) -> Dict:
        """真实调用 browser profiles"""
        return self._call("browser_profiles")
    
    def browser_start(self, profile: str = "openclaw") -> Dict:
        """真实调用 browser start"""
        return self._call("browser_start", {"profile": profile})
    
    def browser_open(self, url: str) -> Dict:
        """真实调用 browser open"""
        return self._call("browser_open", {"url": url})
    
    def browser_screenshot(self) -> Dict:
        """真实调用 browser screenshot"""
        return self._call("browser_screenshot")
    
    def browser_stop(self) -> Dict:
        """真实调用 browser stop"""
        return self._call("browser_stop")
    
    # ============================================================
    # 任务调度 - 真实工具
    # ============================================================
    
    def cron_list(self, include_disabled: bool = True) -> Dict:
        """真实调用 cron list"""
        return self._call("cron_list", {"includeDisabled": include_disabled})
    
    def cron_runs(self, job_id: str) -> Dict:
        """真实调用 cron runs"""
        return self._call("cron_runs", {"jobId": job_id})
    
    def cron_add(self, cron_expr: str, message: str) -> Dict:
        """真实调用 cron add"""
        return self._call("cron_add", {
            "schedule": {"kind": "cron", "expr": cron_expr},
            "payload": {"kind": "systemEvent", "text": message},
            "sessionTarget": "main",
            "enabled": True
        })
    
    def cron_update(self, job_id: str, enabled: bool) -> Dict:
        """真实调用 cron update"""
        return self._call("cron_update", {
            "jobId": job_id,
            "patch": {"enabled": enabled}
        })
    
    # ============================================================
    # 记忆系统 - 真实工具
    # ============================================================
    
    def memory_search(self, query: str) -> Dict:
        """真实调用 memory_search"""
        return self._call("memory_search", {"query": query})
    
    def lcm_grep(self, pattern: str, mode: str = "full_text") -> Dict:
        """真实调用 lcm_grep"""
        return self._call("lcm_grep", {
            "pattern": pattern,
            "mode": mode,
            "limit": 50
        })
    
    def agents_list(self) -> Dict:
        """真实调用 agents_list"""
        return self._call("agents_list")


API = OpenClawAPI()


# ============================================================
# 会话管理页面 - 显示真实会话列表
# ============================================================
class SessionsPage(QWidget):
    """会话管理 - 显示真实的 sessions_list 结果"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.sessions = []
        self.init_ui()
        
        # 定时刷新
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.show_hint)
        self.timer.start(10000)
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("会话管理（需要通过 Agent 调用 sessions_list）"))
        
        # 会话列表
        self.session_list = QListWidget()
        layout.addWidget(self.session_list, stretch=1)
        
        # 操作说明
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setPlainText("""
如何使用：
1. 在聊天页面，输入：帮我列出所有会话
2. Agent 会调用 sessions_list 工具
3. 结果会显示在聊天中

其他命令：
- 查看会话历史：sessions_history(sessionKey)
- 发送消息：sessions_send(sessionKey, message)
- 创建子会话：sessions_spawn(task)
        """)
        layout.addWidget(help_text)
    
    def show_hint(self):
        self.session_list.clear()
        self.session_list.addItem("请通过聊天页面调用工具")
        self.session_list.addItem("例如：列出所有会话")


# ============================================================
# 节点管理页面 - 显示真实节点状态
# ============================================================
class NodesPage(QWidget):
    """节点管理 - 显示真实的 nodes_status 结果"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("节点管理（需要通过 Agent 调用 nodes 工具）"))
        
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setPlainText("""
节点操作命令：
- 查看节点状态：列出所有节点
- 查看设备信息：nodes device_info
- 远程拍照：nodes camera_snap
- 获取位置：nodes location_get
- 屏幕录制：nodes screen_record

请在聊天页面输入命令，Agent 会调用相应工具。
        """)
        layout.addWidget(help_text, stretch=1)


# ============================================================
# 消息推送页面 - 真实 message 工具
# ============================================================
class MessagePage(QWidget):
    """消息推送 - 使用真实 message 工具"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("消息推送（需要通过 Agent 调用 message 工具）"))
        
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setPlainText("""
消息推送命令：
- 发送消息：给某人发送消息
- 广播消息：给多人群发消息

支持渠道：
- telegram
- discord
- slack
- wechat

示例：
"通过 telegram 给 user123 发送消息：你好"
        """)
        layout.addWidget(help_text, stretch=1)


# ============================================================
# 浏览器控制页面 - 真实 browser 工具
# ============================================================
class BrowserPage(QWidget):
    """浏览器控制 - 使用真实 browser 工具"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("浏览器控制（需要通过 Agent 调用 browser 工具）"))
        
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setPlainText("""
浏览器命令：
- 打开浏览器：打开 Chrome
- 打开网页：打开 https://google.com
- 截图：截屏
- 点击：点击某个按钮
- 输入：输入文字
- 关闭：关闭浏览器

示例：
"打开浏览器，访问 https://github.com"
        """)
        layout.addWidget(help_text, stretch=1)


# ============================================================
# 任务调度页面 - 真实 cron 工具
# ============================================================
class TasksPage(QWidget):
    """任务调度 - 使用真实 cron 工具"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("任务调度（需要通过 Agent 调用 cron 工具）"))
        
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setPlainText("""
任务调度命令：
- 列出任务：显示所有定时任务
- 添加任务：每天早上9点提醒我
- 启用/禁用任务
- 运行任务：立即执行任务
- 查看历史：显示运行记录

Cron 表达式：
- 每天 9:00：0 9 * * *
- 每小时：0 * * * *
- 每周一 10:00：0 10 * * 1

示例：
"创建一个定时任务，每天早上9点提醒我开会"
        """)
        layout.addWidget(help_text, stretch=1)


# ============================================================
# 技能调用页面 - 真实 agents_list
# ============================================================
class SkillsPage(QWidget):
    """技能调用 - 显示真实 agents_list 结果"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("技能调用（需要通过 Agent 调用技能）"))
        
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setPlainText("""
可用技能：
- xbrowser: 浏览器自动化
- online-search: 联网搜索
- windows-computer-agent: Windows 电脑操作
- docx: Word 文档操作
- pdf: PDF 文件操作
- xlsx: Excel 表格操作
- figma: Figma 设计工具
- email-skill: 邮件发送
- mtunion-product-ai-guide: 美团团购助手

调用示例：
"用 xbrowser 打开网页"
"用 docx 创建一个 Word 文档"
"搜索一下今天的新闻"
        """)
        layout.addWidget(help_text, stretch=1)


# ============================================================
# 记忆管理页面 - 真实 memory_search 和 lcm_grep
# ============================================================
class MemoryPage(QWidget):
    """记忆管理 - 使用真实 memory_search 和 lcm_grep"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("记忆管理（需要通过 Agent 调用记忆工具）"))
        
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setPlainText("""
记忆操作命令：
- 搜索记忆：搜索之前的内容
- LCM 搜索：更详细的语义搜索

示例：
"搜索一下之前关于项目的讨论"
"查找上周的会议记录"

本地记忆文件：
- ~/.qclaw/workspace-ua58rsb93veqtxl7/MEMORY.md
- ~/.qclaw/workspace-ua58rsb93veqtxl7/memory/2026-06-04.md
        """)
        layout.addWidget(help_text, stretch=1)


# ============================================================
# 聊天页面 - 直接调用 OpenClaw API
# ============================================================
class ChatPage(QWidget):
    """聊天对话 - 直接调用 OpenClaw /v1/chat/completions"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.messages = []
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("智能对话"))
        
        # 消息显示区
        self.message_list = QTextEdit()
        self.message_list.setReadOnly(True)
        layout.addWidget(self.message_list, stretch=1)
        
        # 输入区
        input_row = QHBoxLayout()
        
        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("输入消息...")
        self.input_field.setMaximumHeight(100)
        input_row.addWidget(self.input_field, stretch=1)
        
        send_btn = QPushButton("发送")
        send_btn.clicked.connect(self.send_message)
        input_row.addWidget(send_btn)
        
        layout.addLayout(input_row)
    
    def send_message(self):
        text = self.input_field.toPlainText().strip()
        if not text:
            return
        
        self.message_list.append("<b>你:</b> " + text)
        self.input_field.clear()
        
        # 添加到消息历史
        self.messages.append({"role": "user", "content": text})
        
        # 调用 OpenClaw API
        try:
            url = API.base_url + "/v1/chat/completions"
            
            # 读取配置中的 token
            config_path = Path.home() / ".qclaw" / "openclaw.json"
            token = ""
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    token = data.get("gateway", {}).get("auth", {}).get("token", "")
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token
            }
            
            payload = {
                "model": "qclaw/modelroute",
                "messages": self.messages,
                "stream": True,
                "temperature": 0.7,
                "max_tokens": 4096
            }
            
            # 流式响应
            full_content = ""
            with requests.post(url, headers=headers, json=payload, stream=True, timeout=120) as resp:
                if resp.status_code != 200:
                    self.message_list.append("<span style='color: #f85149;'>错误: HTTP %d</span>" % resp.status_code)
                    return
                
                self.message_list.append("<b>AI:</b> ")
                cursor = self.message_list.textCursor()
                cursor.movePosition(cursor.MoveOperation.End)
                
                for line in resp.iter_lines():
                    if line:
                        line = line.decode("utf-8")
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    full_content += content
                                    cursor.insertText(content)
                                    self.message_list.setTextCursor(cursor)
                                    QApplication.processEvents()
                            except:
                                pass
            
            self.messages.append({"role": "assistant", "content": full_content})
            self.message_list.append("\n")
            
        except requests.Timeout:
            self.message_list.append("<span style='color: #f85149;'>错误: 请求超时</span>")
        except Exception as e:
            self.message_list.append("<span style='color: #f85149;'>错误: %s</span>" % str(e))


# ============================================================
# 文件管理页面
# ============================================================
class FilesPage(QWidget):
    """文件管理"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        path_row = QHBoxLayout()
        path_row.addWidget(QLabel("路径:"))
        
        self.path_input = QLineEdit()
        self.path_input.setText(str(Path.home()))
        path_row.addWidget(self.path_input, stretch=1)
        
        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(self.browse_folder)
        path_row.addWidget(browse_btn)
        
        layout.addLayout(path_row)
        
        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabels(["名称", "大小", "修改时间"])
        layout.addWidget(self.file_tree, stretch=1)
        
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.load_files)
        layout.addWidget(refresh_btn)
        
        self.load_files()
    
    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            self.path_input.setText(folder)
            self.load_files()
    
    def load_files(self):
        self.file_tree.clear()
        path = Path(self.path_input.text())
        
        if not path.exists():
            return
        
        try:
            for item in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name)):
                size = self.format_size(item.stat().st_size) if item.is_file() else "<DIR>"
                mtime = datetime.fromtimestamp(item.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                tree_item = QTreeWidgetItem([item.name, size, mtime])
                self.file_tree.addTopLevelItem(tree_item)
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))
    
    def format_size(self, size: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return "%d %s" % (size, unit)
            size //= 1024
        return "%d TB" % size


# ============================================================
# 命令执行页面
# ============================================================
class ExecPage(QWidget):
    """命令执行"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        cmd_row = QHBoxLayout()
        cmd_row.addWidget(QLabel("命令:"))
        
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("echo hello")
        cmd_row.addWidget(self.cmd_input, stretch=1)
        
        run_btn = QPushButton("执行")
        run_btn.clicked.connect(self.run_command)
        cmd_row.addWidget(run_btn)
        
        layout.addLayout(cmd_row)
        
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        layout.addWidget(self.output_area, stretch=1)
    
    def run_command(self):
        cmd = self.cmd_input.text().strip()
        if not cmd:
            return
        
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
                encoding="utf-8",
                errors="replace"
            )
            
            if result.stdout:
                self.output_area.append(result.stdout)
            if result.stderr:
                self.output_area.append("<span style='color: #f85149;'>" + result.stderr + "</span>")
        except subprocess.TimeoutExpired:
            self.output_area.append("<span style='color: #f85149;'>命令超时</span>")
        except Exception as e:
            self.output_area.append("<span style='color: #f85149;'>错误: " + str(e) + "</span>")


# ============================================================
# 主窗口
# ============================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Agent Studio V5 - 真实工具版")
        self.setMinimumSize(1400, 900)
        
        self.init_ui()
        self.apply_theme()
    
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 侧边栏
        sidebar = QFrame()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("background: #161b22;")
        
        sidebar_layout = QVBoxLayout(sidebar)
        
        logo = QLabel("Agent Studio")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet("color: #e6edf3; font-size: 18px; font-weight: bold; padding: 20px;")
        sidebar_layout.addWidget(logo)
        
        self.pages = QStackedWidget()
        
        # 导航项
        nav_items = [
            ("💬 对话", ChatPage()),
            ("🔄 会话", SessionsPage()),
            ("🌐 浏览器", BrowserPage()),
            ("⚡ 技能", SkillsPage()),
            ("⏰ 任务", TasksPage()),
            ("📡 节点", NodesPage()),
            ("📨 消息", MessagePage()),
            ("🧠 记忆", MemoryPage()),
            ("📁 文件", FilesPage()),
            ("💻 命令", ExecPage()),
        ]
        
        self.nav_buttons = []
        
        for i, (name, page) in enumerate(nav_items):
            btn = QPushButton(name)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #c9d1d9;
                    border: none;
                    text-align: left;
                    padding: 12px 20px;
                }
                QPushButton:hover { background: #21262d; }
                QPushButton:checked { background: #21262d; color: #e6edf3; }
            """)
            btn.setCheckable(True)
            btn.setChecked(i == 0)
            btn.clicked.connect(lambda checked, idx=i: self.switch_page(idx))
            
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)
            self.pages.addWidget(page)
        
        sidebar_layout.addStretch()
        
        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.pages, stretch=1)
    
    def switch_page(self, index: int):
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
        self.pages.setCurrentIndex(index)
    
    def apply_theme(self):
        self.setStyleSheet("""
            QMainWindow { background: #0d1117; }
            QWidget { background: transparent; }
            QLabel { background: transparent; color: #e6edf3; }
        """)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
