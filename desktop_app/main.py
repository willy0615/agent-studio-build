#!/usr/bin/env python3
"""
Agent Studio V5 - 完整真实实现版
所有功能都真实调用 OpenClaw 工具，无硬编码，无虚假 API
"""

import sys
import os
import json
import base64
import subprocess
import traceback
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
from io import BytesIO

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QComboBox, QLineEdit, QCheckBox,
    QListWidget, QListWidgetItem, QStackedWidget, QTableWidget, QTableWidgetItem,
    QFrame, QScrollArea, QHeaderView, QGroupBox, QFormLayout, QMessageBox,
    QTreeWidget, QTreeWidgetItem, QSplitter, QFileDialog, QSpinBox,
    QDoubleSpinBox, QProgressBar, QTabWidget, QPlainTextEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QColor, QPalette, QFont, QTextCursor, QPixmap, QImage

import requests
from PIL import Image


# ============================================================
# 配置
# ============================================================
def load_openclaw_config():
    config_path = Path.home() / ".qclaw" / "openclaw.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            gateway = data.get("gateway", {})
            return {
                "base_url": gateway.get("url", "http://127.0.0.1:52402"),
                "token": gateway.get("auth", {}).get("token", "")
            }
    return {"base_url": "http://127.0.0.1:52402", "token": ""}


CONFIG = load_openclaw_config()


# ============================================================
# 记忆管理器（真实本地实现）
# ============================================================
class MemoryManager:
    def __init__(self, workspace=None):
        if workspace:
            self.workspace = Path(workspace)
        else:
            self.workspace = Path.home() / ".agent_studio"
        self.workspace.mkdir(parents=True, exist_ok=True)
        
        self.memory_file = self.workspace / "MEMORY.md"
        self.memory_dir = self.workspace / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
    
    def load_memory(self) -> str:
        if self.memory_file.exists():
            with open(self.memory_file, "r", encoding="utf-8") as f:
                return f.read()
        return ""
    
    def save_memory(self, content: str):
        with open(self.memory_file, "w", encoding="utf-8") as f:
            f.write(content)
    
    def append_today_log(self, content: str):
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.memory_dir / f"{today}.md"
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = "\n## %s\n%s\n" % (timestamp, content)
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(entry)
    
    def load_today_log(self) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.memory_dir / f"{today}.md"
        if log_file.exists():
            with open(log_file, "r", encoding="utf-8") as f:
                return f.read()
        return ""


MEMORY = MemoryManager()


# ============================================================
# xbrowser CLI 封装（真实调用）
# ============================================================
class XBrowserCLI:
    """真实调用 xbrowser CLI"""
    
    @staticmethod
    def execute(args: str, timeout: int = 60) -> Dict:
        """执行 xb CLI 命令"""
        try:
            node_binary = os.environ.get("QCLAW_CLI_NODE_BINARY", "node")
            cmd = "%s %s" % (node_binary, args)
            
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace"
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "命令超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def init() -> Dict:
        """初始化环境"""
        return XBrowserCLI.execute("xb init", 10)
    
    @staticmethod
    def open(url: str) -> Dict:
        """打开网页"""
        return XBrowserCLI.execute("xb open \"%s\"" % url, 30)
    
    @staticmethod
    def screenshot() -> Dict:
        """截图"""
        return XBrowserCLI.execute("xb screenshot", 10)
    
    @staticmethod
    def click(selector: str) -> Dict:
        """点击元素"""
        return XBrowserCLI.execute("xb click \"%s\"" % selector, 10)
    
    @staticmethod
    def type_text(selector: str, text: str) -> Dict:
        """输入文字"""
        return XBrowserCLI.execute("xb type \"%s\" \"%s\"" % (selector, text), 10)
    
    @staticmethod
    def scrape(selector: str = None) -> Dict:
        """抓取页面内容"""
        if selector:
            return XBrowserCLI.execute("xb scrape \"%s\"" % selector, 15)
        return XBrowserCLI.execute("xb scrape", 15)
    
    @staticmethod
    def close() -> Dict:
        """关闭浏览器"""
        return XBrowserCLI.execute("xb close", 10)


# ============================================================
# 技能调用器（真实通过 OpenClaw API）
# ============================================================
class SkillInvoker:
    """真实调用技能（通过 OpenClaw API）"""
    
    @staticmethod
    def invoke(skill_name: str, params: Dict, timeout: int = 300) -> Dict:
        """调用技能"""
        try:
            url = CONFIG["base_url"] + "/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + CONFIG["token"]
            }
            
            # 构造让 Agent 调用技能的消息
            message = "请使用 %s 技能完成以下任务：\n\n参数：\n%s" % (
                skill_name,
                json.dumps(params, ensure_ascii=False, indent=2)
            )
            
            payload = {
                "model": "qclaw/modelroute",
                "messages": [{"role": "user", "content": message}],
                "max_tokens": 8192,
                "temperature": 0.3
            }
            
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
            
            if resp.status_code != 200:
                return {
                    "success": False,
                    "error": "API 错误 %d: %s" % (resp.status_code, resp.text[:200])
                }
            
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            return {
                "success": True,
                "result": content
            }
            
        except requests.Timeout:
            return {"success": False, "error": "调用超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ============================================================
# 任务调度器（真实通过 OpenClaw cron API）
# ============================================================
class CronScheduler:
    """真实任务调度（通过 OpenClaw cron API）"""
    
    def __init__(self):
        self.base_url = CONFIG["base_url"]
        self.token = CONFIG["token"]
    
    def _headers(self) -> Dict:
        return {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self.token
        }
    
    def list_jobs(self) -> List[Dict]:
        """获取所有任务"""
        try:
            url = self.base_url + "/cron/list"
            resp = requests.get(url, headers=self._headers(), timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                return data.get("jobs", [])
            return []
        except:
            return []
    
    def add_job(self, cron_expr: str, message: str, agent_id: str = "main") -> Dict:
        """添加任务"""
        try:
            url = self.base_url + "/cron/add"
            payload = {
                "cron": cron_expr,
                "message": message,
                "agentId": agent_id
            }
            
            resp = requests.post(url, headers=self._headers(), json=payload, timeout=10)
            
            if resp.status_code == 200:
                return {"success": True, "data": resp.json()}
            return {"success": False, "error": "HTTP %d" % resp.status_code}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def update_job(self, job_id: str, updates: Dict) -> Dict:
        """更新任务"""
        try:
            url = self.base_url + "/cron/update"
            payload = {"jobId": job_id}
            payload.update(updates)
            
            resp = requests.post(url, headers=self._headers(), json=payload, timeout=10)
            
            if resp.status_code == 200:
                return {"success": True}
            return {"success": False, "error": "HTTP %d" % resp.status_code}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def remove_job(self, job_id: str) -> bool:
        """删除任务"""
        try:
            url = self.base_url + "/cron/remove"
            resp = requests.post(url, headers=self._headers(), json={"jobId": job_id}, timeout=10)
            return resp.status_code == 200
        except:
            return False


CRON = CronScheduler()


# ============================================================
# 工作线程
# ============================================================
class ChatWorker(QThread):
    """聊天工作线程"""
    chunk_received = pyqtSignal(str)
    result_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, messages: List[Dict], stream: bool = True):
        super().__init__()
        self.messages = messages
        self.stream = stream
    
    def run(self):
        try:
            url = CONFIG["base_url"] + "/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + CONFIG["token"]
            }
            payload = {
                "model": "qclaw/modelroute",
                "messages": self.messages,
                "stream": self.stream,
                "temperature": 0.7,
                "max_tokens": 4096
            }
            
            resp = requests.post(url, headers=headers, json=payload, 
                                stream=self.stream, timeout=120)
            
            if resp.status_code != 200:
                self.error_occurred.emit("API 错误 %d: %s" % (resp.status_code, resp.text[:200]))
                return
            
            if self.stream:
                full_content = ""
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
                                    self.chunk_received.emit(content)
                            except:
                                pass
                self.result_ready.emit(full_content)
            else:
                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                self.result_ready.emit(content)
                
        except Exception as e:
            self.error_occurred.emit(str(e))


class BrowserWorker(QThread):
    """浏览器工作线程 - 真实调用 xbrowser"""
    progress = pyqtSignal(str)
    screenshot_ready = pyqtSignal(str)
    result_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, action: str, params: Dict = None):
        super().__init__()
        self.action = action
        self.params = params or {}
    
    def run(self):
        try:
            if self.action == "init":
                self.progress.emit("初始化浏览器环境...")
                result = XBrowserCLI.init()
                self.result_ready.emit(result)
                
            elif self.action == "open":
                url = self.params.get("url", "https://www.google.com")
                self.progress.emit("正在打开: " + url)
                result = XBrowserCLI.open(url)
                
                if result["success"]:
                    self.result_ready.emit({"success": True, "message": "页面已打开"})
                else:
                    self.error_occurred.emit(result.get("stderr", "打开失败"))
                    
            elif self.action == "screenshot":
                self.progress.emit("正在截图...")
                result = XBrowserCLI.screenshot()
                
                if result["success"]:
                    # 解析截图路径
                    output = result["stdout"]
                    if "saved to:" in output:
                        path = output.split("saved to:")[-1].strip()
                        # 读取图片
                        with open(path, "rb") as f:
                            img_data = f.read()
                        img_base64 = base64.b64encode(img_data).decode("utf-8")
                        self.screenshot_ready.emit(img_base64)
                    self.result_ready.emit({"success": True})
                else:
                    self.error_occurred.emit(result.get("stderr", "截图失败"))
                    
            elif self.action == "click":
                selector = self.params.get("selector", "")
                self.progress.emit("正在点击: " + selector)
                result = XBrowserCLI.click(selector)
                
                if result["success"]:
                    self.result_ready.emit({"success": True, "message": "点击完成"})
                else:
                    self.error_occurred.emit(result.get("stderr", "点击失败"))
                    
            elif self.action == "type":
                selector = self.params.get("selector", "")
                text = self.params.get("text", "")
                self.progress.emit("正在输入文字...")
                result = XBrowserCLI.type_text(selector, text)
                
                if result["success"]:
                    self.result_ready.emit({"success": True, "message": "输入完成"})
                else:
                    self.error_occurred.emit(result.get("stderr", "输入失败"))
                    
            elif self.action == "scrape":
                self.progress.emit("正在抓取页面内容...")
                selector = self.params.get("selector")
                result = XBrowserCLI.scrape(selector)
                
                if result["success"]:
                    content = result["stdout"]
                    self.result_ready.emit({"success": True, "content": content})
                else:
                    self.error_occurred.emit(result.get("stderr", "抓取失败"))
                    
            elif self.action == "close":
                self.progress.emit("正在关闭浏览器...")
                result = XBrowserCLI.close()
                self.result_ready.emit({"success": result["success"]})
                
        except Exception as e:
            self.error_occurred.emit(str(e))


class SkillWorker(QThread):
    """技能调用工作线程"""
    progress = pyqtSignal(str)
    result_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, skill_name: str, params: Dict):
        super().__init__()
        self.skill_name = skill_name
        self.params = params
    
    def run(self):
        try:
            self.progress.emit("正在调用技能: " + self.skill_name)
            result = SkillInvoker.invoke(self.skill_name, self.params)
            
            if result["success"]:
                self.result_ready.emit(result)
            else:
                self.error_occurred.emit(result.get("error", "调用失败"))
                
        except Exception as e:
            self.error_occurred.emit(str(e))


class ExecWorker(QThread):
    """命令执行工作线程"""
    progress = pyqtSignal(str)
    output_ready = pyqtSignal(str, str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, command: str, cwd: str = None, timeout: int = 60):
        super().__init__()
        self.command = command
        self.cwd = cwd
        self.timeout = timeout
    
    def run(self):
        try:
            self.progress.emit("正在执行: " + self.command)
            
            result = subprocess.run(
                self.command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=self.cwd,
                timeout=self.timeout,
                encoding="utf-8",
                errors="replace"
            )
            
            self.output_ready.emit(result.stdout, result.stderr)
            MEMORY.append_today_log("**命令执行**: %s\n" % self.command)
            
        except subprocess.TimeoutExpired:
            self.error_occurred.emit("命令超时")
        except Exception as e:
            self.error_occurred.emit(str(e))


# ============================================================
# 页面
# ============================================================
class ChatPage(QWidget):
    """聊天页面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.messages = []
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("💬 智能对话")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #e6edf3;")
        layout.addWidget(title)
        
        self.message_list = QTextEdit()
        self.message_list.setReadOnly(True)
        self.message_list.setStyleSheet("""
            QTextEdit {
                background: #0d1117;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        layout.addWidget(self.message_list, stretch=1)
        
        input_row = QHBoxLayout()
        
        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("输入消息...")
        self.input_field.setMaximumHeight(100)
        self.input_field.setStyleSheet("""
            QTextEdit {
                background: #0d1117;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        input_row.addWidget(self.input_field, stretch=1)
        
        send_btn = QPushButton("发送")
        send_btn.setStyleSheet("""
            QPushButton {
                background: #238636;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-weight: bold;
            }
            QPushButton:hover { background: #2ea043; }
        """)
        send_btn.clicked.connect(self.send_message)
        input_row.addWidget(send_btn)
        
        layout.addLayout(input_row)
    
    def send_message(self):
        text = self.input_field.toPlainText().strip()
        if not text:
            return
        
        self.message_list.append("<b>你:</b> " + text)
        self.input_field.clear()
        
        self.messages.append({"role": "user", "content": text})
        
        worker = ChatWorker(self.messages)
        worker.chunk_received.connect(self.on_chunk)
        worker.result_ready.connect(self.on_result)
        worker.error_occurred.connect(self.on_error)
        worker.start()
        
        self.current_worker = worker
    
    def on_chunk(self, chunk: str):
        cursor = self.message_list.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(chunk)
        self.message_list.setTextCursor(cursor)
    
    def on_result(self, content: str):
        self.messages.append({"role": "assistant", "content": content})
        self.message_list.append("\n")
        MEMORY.append_today_log("**对话**: %s\n" % content[:100])
    
    def on_error(self, error: str):
        self.message_list.append("\n<b style='color: #f85149;'>错误:</b> " + error)


class BrowserPage(QWidget):
    """浏览器自动化页面 - 真实调用 xbrowser"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("🌐 浏览器自动化")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #e6edf3;")
        layout.addWidget(title)
        
        # 截图显示
        self.screenshot_label = QLabel("点击「打开网页」开始")
        self.screenshot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.screenshot_label.setMinimumHeight(400)
        self.screenshot_label.setStyleSheet("""
            QLabel {
                background: #0d1117;
                border: 2px dashed #30363d;
                border-radius: 8px;
                color: #8b949e;
            }
        """)
        layout.addWidget(self.screenshot_label)
        
        # URL 输入
        url_row = QHBoxLayout()
        url_row.addWidget(QLabel("网址:"))
        
        self.url_input = QLineEdit()
        self.url_input.setText("https://www.google.com")
        self.url_input.setStyleSheet("""
            QLineEdit {
                background: #0d1117;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        url_row.addWidget(self.url_input, stretch=1)
        
        open_btn = QPushButton("打开")
        open_btn.setStyleSheet("""
            QPushButton {
                background: #238636;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
            }
        """)
        open_btn.clicked.connect(self.open_page)
        url_row.addWidget(open_btn)
        
        layout.addLayout(url_row)
        
        # 操作按钮
        btn_row = QHBoxLayout()
        
        screenshot_btn = QPushButton("📸 截图")
        screenshot_btn.clicked.connect(self.take_screenshot)
        btn_row.addWidget(screenshot_btn)
        
        scrape_btn = QPushButton("📄 抓取")
        scrape_btn.clicked.connect(self.scrape_page)
        btn_row.addWidget(scrape_btn)
        
        close_btn = QPushButton("❌ 关闭")
        close_btn.clicked.connect(self.close_browser)
        btn_row.addWidget(close_btn)
        
        layout.addLayout(btn_row)
        
        # 结果显示
        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        self.result_area.setMaximumHeight(150)
        self.result_area.setStyleSheet("""
            QTextEdit {
                background: #0d1117;
                color: #e6edf3;
                border: 1px solid #30363d;
            }
        """)
        layout.addWidget(self.result_area)
    
    def open_page(self):
        url = self.url_input.text().strip()
        worker = BrowserWorker("open", {"url": url})
        worker.progress.connect(self.on_progress)
        worker.result_ready.connect(self.on_result)
        worker.error_occurred.connect(self.on_error)
        worker.start()
        self.current_worker = worker
    
    def take_screenshot(self):
        worker = BrowserWorker("screenshot")
        worker.progress.connect(self.on_progress)
        worker.screenshot_ready.connect(self.on_screenshot)
        worker.result_ready.connect(self.on_result)
        worker.error_occurred.connect(self.on_error)
        worker.start()
        self.current_worker = worker
    
    def scrape_page(self):
        worker = BrowserWorker("scrape")
        worker.progress.connect(self.on_progress)
        worker.result_ready.connect(self.on_scrape_result)
        worker.error_occurred.connect(self.on_error)
        worker.start()
        self.current_worker = worker
    
    def close_browser(self):
        worker = BrowserWorker("close")
        worker.progress.connect(self.on_progress)
        worker.result_ready.connect(self.on_result)
        worker.start()
        self.current_worker = worker
    
    def on_progress(self, msg: str):
        self.result_area.append(msg)
    
    def on_screenshot(self, img_base64: str):
        img_data = base64.b64decode(img_base64)
        pixmap = QPixmap()
        pixmap.loadFromData(img_data)
        self.screenshot_label.setPixmap(pixmap.scaled(
            self.screenshot_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))
    
    def on_result(self, result: Dict):
        self.result_area.append("✅ 完成")
    
    def on_scrape_result(self, result: Dict):
        content = result.get("content", "")
        self.result_area.append(content[:500])
    
    def on_error(self, error: str):
        self.result_area.append("❌ " + error)


class SkillsPage(QWidget):
    """技能调用页面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("⚡ 技能调用")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #e6edf3;")
        layout.addWidget(title)
        
        # 技能选择
        form = QFormLayout()
        
        self.skill_combo = QComboBox()
        self.skill_combo.addItems([
            "pdf - PDF 处理",
            "xlsx - Excel 表格",
            "docx - Word 文档",
            "online-search - 在线搜索",
            "windows-computer-agent - 电脑操作"
        ])
        self.skill_combo.setStyleSheet("""
            QComboBox {
                background: #0d1117;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        form.addRow("技能:", self.skill_combo)
        
        self.params_input = QTextEdit()
        self.params_input.setPlaceholderText('{"param1": "value1"}')
        self.params_input.setMaximumHeight(100)
        self.params_input.setStyleSheet("""
            QTextEdit {
                background: #0d1117;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        form.addRow("参数:", self.params_input)
        
        layout.addLayout(form)
        
        # 调用按钮
        invoke_btn = QPushButton("调用技能")
        invoke_btn.setStyleSheet("""
            QPushButton {
                background: #238636;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-weight: bold;
            }
        """)
        invoke_btn.clicked.connect(self.invoke_skill)
        layout.addWidget(invoke_btn)
        
        # 结果
        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        self.result_area.setStyleSheet("""
            QTextEdit {
                background: #0d1117;
                color: #e6edf3;
                border: 1px solid #30363d;
            }
        """)
        layout.addWidget(self.result_area, stretch=1)
    
    def invoke_skill(self):
        skill_text = self.skill_combo.currentText()
        skill_name = skill_text.split(" - ")[0]
        
        params_text = self.params_input.toPlainText().strip()
        try:
            params = json.loads(params_text) if params_text else {}
        except:
            params = {"input": params_text}
        
        worker = SkillWorker(skill_name, params)
        worker.progress.connect(self.on_progress)
        worker.result_ready.connect(self.on_result)
        worker.error_occurred.connect(self.on_error)
        worker.start()
        self.current_worker = worker
    
    def on_progress(self, msg: str):
        self.result_area.append(msg)
    
    def on_result(self, result: Dict):
        content = result.get("result", "")
        self.result_area.append("✅ 结果:\n" + content[:1000])
    
    def on_error(self, error: str):
        self.result_area.append("❌ 错误: " + error)


class TasksPage(QWidget):
    """任务调度页面 - 真实调用 OpenClaw cron API"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_tasks()
        
        # 自动刷新
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.load_tasks)
        self.refresh_timer.start(10000)  # 每10秒刷新
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("⏰ 任务调度")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #e6edf3;")
        layout.addWidget(title)
        
        # 任务表格
        self.tasks_table = QTableWidget()
        self.tasks_table.setColumnCount(5)
        self.tasks_table.setHorizontalHeaderLabels(["ID", "Cron", "消息", "状态", "操作"])
        self.tasks_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tasks_table.setStyleSheet("""
            QTableWidget {
                background: #0d1117;
                color: #e6edf3;
                border: 1px solid #30363d;
                gridline-color: #30363d;
            }
            QHeaderView::section {
                background: #161b22;
                color: #e6edf3;
                border: none;
                padding: 8px;
            }
        """)
        layout.addWidget(self.tasks_table, stretch=1)
        
        # 添加任务
        add_group = QGroupBox("添加新任务")
        add_layout = QFormLayout(add_group)
        
        self.cron_input = QLineEdit()
        self.cron_input.setPlaceholderText("0 9 * * *")
        self.cron_input.setStyleSheet("background: #0d1117; color: #e6edf3; border: 1px solid #30363d; padding: 8px;")
        add_layout.addRow("Cron:", self.cron_input)
        
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("每天早上9点提醒我...")
        self.message_input.setStyleSheet("background: #0d1117; color: #e6edf3; border: 1px solid #30363d; padding: 8px;")
        add_layout.addRow("消息:", self.message_input)
        
        add_btn = QPushButton("添加")
        add_btn.setStyleSheet("background: #238636; color: white; border: none; border-radius: 6px; padding: 10px 20px;")
        add_btn.clicked.connect(self.add_task)
        add_layout.addRow(add_btn)
        
        layout.addWidget(add_group)
    
    def load_tasks(self):
        jobs = CRON.list_jobs()
        self.tasks_table.setRowCount(len(jobs))
        
        for i, job in enumerate(jobs):
            self.tasks_table.setItem(i, 0, QTableWidgetItem(job.get("jobId", "")))
            self.tasks_table.setItem(i, 1, QTableWidgetItem(job.get("cron", "")))
            self.tasks_table.setItem(i, 2, QTableWidgetItem(job.get("message", "")[:30]))
            
            status = "启用" if job.get("enabled", True) else "禁用"
            status_item = QTableWidgetItem(status)
            status_item.setForeground(QColor("#3fb950") if job.get("enabled", True) else QColor("#f85149")))
            self.tasks_table.setItem(i, 3, status_item)
            
            # 操作按钮
            toggle_btn = QPushButton("切换" if job.get("enabled", True) else "启用")
            toggle_btn.clicked.connect(lambda checked, jid=job.get("jobId"): self.toggle_task(jid))
            self.tasks_table.setCellWidget(i, 4, toggle_btn)
    
    def add_task(self):
        cron_expr = self.cron_input.text().strip()
        message = self.message_input.text().strip()
        
        if not cron_expr or not message:
            QMessageBox.warning(self, "提示", "请填写完整")
            return
        
        result = CRON.add_job(cron_expr, message)
        
        if result["success"]:
            QMessageBox.information(self, "成功", "任务已添加")
            self.load_tasks()
        else:
            QMessageBox.critical(self, "失败", result.get("error", "未知错误"))
    
    def toggle_task(self, job_id: str):
        # 获取当前状态
        jobs = CRON.list_jobs()
        current_enabled = True
        for job in jobs:
            if job.get("jobId") == job_id:
                current_enabled = job.get("enabled", True)
                break
        
        # 切换状态
        result = CRON.update_job(job_id, {"enabled": not current_enabled})
        
        if result["success"]:
            self.load_tasks()
        else:
            QMessageBox.critical(self, "失败", result.get("error", "未知错误"))


class MemoryPage(QWidget):
    """记忆管理页面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("🧠 记忆系统")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #e6edf3;")
        layout.addWidget(title)
        
        tabs = QTabWidget()
        
        # MEMORY.md 标签
        memory_tab = QWidget()
        memory_layout = QVBoxLayout(memory_tab)
        
        self.memory_editor = QTextEdit()
        self.memory_editor.setStyleSheet("""
            QTextEdit {
                background: #0d1117;
                color: #e6edf3;
                border: 1px solid #30363d;
                font-family: 'Consolas', monospace;
            }
        """)
        memory_layout.addWidget(self.memory_editor)
        
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.save_memory)
        memory_layout.addWidget(save_btn)
        
        tabs.addTab(memory_tab, "长期记忆")
        
        # 日志标签
        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)
        
        self.log_editor = QTextEdit()
        self.log_editor.setReadOnly(True)
        log_layout.addWidget(self.log_editor)
        
        tabs.addTab(log_tab, "今日日志")
        
        layout.addWidget(tabs)
    
    def load_data(self):
        self.memory_editor.setPlainText(MEMORY.load_memory())
        self.log_editor.setPlainText(MEMORY.load_today_log())
    
    def save_memory(self):
        MEMORY.save_memory(self.memory_editor.toPlainText())
        QMessageBox.information(self, "成功", "记忆已保存")


class FilesPage(QWidget):
    """文件管理页面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("📁 文件管理")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #e6edf3;")
        layout.addWidget(title)
        
        path_row = QHBoxLayout()
        path_row.addWidget(QLabel("路径:"))
        
        self.path_input = QLineEdit()
        self.path_input.setText(str(Path.home()))
        self.path_input.setStyleSheet("background: #0d1117; color: #e6edf3; border: 1px solid #30363d; padding: 8px;")
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


class ExecPage(QWidget):
    """命令执行页面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("💻 命令执行")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #e6edf3;")
        layout.addWidget(title)
        
        cmd_row = QHBoxLayout()
        cmd_row.addWidget(QLabel("命令:"))
        
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("echo hello")
        self.cmd_input.setStyleSheet("background: #0d1117; color: #e6edf3; border: 1px solid #30363d; padding: 8px;")
        cmd_row.addWidget(self.cmd_input, stretch=1)
        
        run_btn = QPushButton("执行")
        run_btn.clicked.connect(self.run_command)
        cmd_row.addWidget(run_btn)
        
        layout.addLayout(cmd_row)
        
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setStyleSheet("""
            QTextEdit {
                background: #0d1117;
                color: #e6edf3;
                border: 1px solid #30363d;
                font-family: 'Consolas', monospace;
            }
        """)
        layout.addWidget(self.output_area, stretch=1)
    
    def run_command(self):
        cmd = self.cmd_input.text().strip()
        if not cmd:
            return
        
        worker = ExecWorker(cmd)
        worker.progress.connect(self.on_progress)
        worker.output_ready.connect(self.on_output)
        worker.error_occurred.connect(self.on_error)
        worker.start()
        self.current_worker = worker
    
    def on_progress(self, msg: str):
        self.output_area.append(msg)
    
    def on_output(self, stdout: str, stderr: str):
        if stdout:
            self.output_area.append(stdout)
        if stderr:
            self.output_area.append("<span style='color: #f85149;'>" + stderr + "</span>")
    
    def on_error(self, error: str):
        self.output_area.append("<span style='color: #f85149;'>错误: " + error + "</span>")


# ============================================================
# 主窗口
# ============================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Agent Studio V5 - 完整真实实现版")
        self.setMinimumSize(1200, 800)
        
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
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        
        logo = QLabel("Agent Studio")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet("color: #e6edf3; font-size: 18px; font-weight: bold; padding: 20px;")
        sidebar_layout.addWidget(logo)
        
        self.pages = QStackedWidget()
        
        nav_items = [
            ("💬 对话", ChatPage()),
            ("🌐 浏览器", BrowserPage()),
            ("⚡ 技能", SkillsPage()),
            ("⏰ 任务", TasksPage()),
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


# ============================================================
# 主入口
# ============================================================
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
