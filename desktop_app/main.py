#!/usr/bin/env python3
"""
Agent Studio V5 - 完整版
功能：聊天 + 电脑操作 + 记忆 + 文件管理 + 真实任务调度 + 浏览器自动化 + 技能调用 + 代码执行
"""

import sys
import os
import json
import time
import base64
import traceback
import subprocess
import threading
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
from PyQt6.QtGui import QColor, QPalette, QFont, QTextCursor

import requests


# ============================================================
# 配置 - 读取 OpenClaw 配置
# ============================================================
def load_openclaw_config():
    """读取 OpenClaw 配置"""
    config = {
        "OPENCLAW_API_URL": "http://127.0.0.1:52402/v1/chat/completions",
        "OPENCLAW_AUTH_TOKEN": "",
        "OPENCLAW_BASE_URL": "http://127.0.0.1:52402",
    }
    
    # 从 openclaw.json 读取 token
    config_path = Path.home() / ".qclaw" / "openclaw.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                gateway = data.get("gateway", {})
                auth = gateway.get("auth", {})
                token = auth.get("token", "")
                if token:
                    config["OPENCLAW_AUTH_TOKEN"] = token
                    config["OPENCLAW_BASE_URL"] = gateway.get("url", "http://127.0.0.1:52402")
                    config["OPENCLAW_API_URL"] = config["OPENCLAW_BASE_URL"] + "/v1/chat/completions"
        except:
            pass
    
    # 从环境变量读取（优先级更高）
    env_token = os.getenv("OPENCLAW_AUTH_TOKEN")
    if env_token:
        config["OPENCLAW_AUTH_TOKEN"] = env_token
    
    return config


CONFIG = load_openclaw_config()


# ============================================================
# OpenClaw API 客户端
# ============================================================
class OpenClawAPI:
    """OpenClaw API 统一客户端"""
    
    def __init__(self):
        self.base_url = CONFIG.get("OPENCLAW_BASE_URL", "http://127.0.0.1:52402")
        self.token = CONFIG.get("OPENCLAW_AUTH_TOKEN", "")
    
    def _headers(self):
        return {
            "Content-Type": "application/json",
            "Authorization": "Bearer %s" % self.token
        }
    
    def chat(self, messages: List[Dict], stream: bool = False, **kwargs) -> Dict:
        """调用聊天 API"""
        url = self.base_url + "/v1/chat/completions"
        payload = {
            "model": kwargs.get("model", "openclaw"),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2048),
            "stream": stream
        }
        resp = requests.post(url, headers=self._headers(), json=payload, timeout=120)
        if resp.status_code != 200:
            raise Exception("API 错误 HTTP %d: %s" % (resp.status_code, resp.text[:200]))
        return resp.json()
    
    def cron_list(self) -> List[Dict]:
        """获取定时任务列表"""
        url = self.base_url + "/cron/list"
        resp = requests.get(url, headers=self._headers(), timeout=30)
        if resp.status_code == 200:
            return resp.json().get("jobs", [])
        return []
    
    def cron_add(self, job: Dict) -> Dict:
        """添加定时任务"""
        url = self.base_url + "/cron/add"
        resp = requests.post(url, headers=self._headers(), json=job, timeout=30)
        if resp.status_code != 200:
            raise Exception("添加任务失败: %s" % resp.text[:200])
        return resp.json()
    
    def cron_remove(self, job_id: str) -> bool:
        """删除定时任务"""
        url = self.base_url + "/cron/remove"
        resp = requests.post(url, headers=self._headers(), json={"jobId": job_id}, timeout=30)
        return resp.status_code == 200
    
    def browser_open(self, url: str) -> Dict:
        """打开浏览器页面"""
        api_url = self.base_url + "/browser/open"
        resp = requests.post(api_url, headers=self._headers(), json={"url": url}, timeout=30)
        if resp.status_code != 200:
            raise Exception("打开浏览器失败: %s" % resp.text[:200])
        return resp.json()
    
    def browser_snapshot(self, tab_id: str = None) -> Dict:
        """获取浏览器快照"""
        url = self.base_url + "/browser/snapshot"
        payload = {"tabId": tab_id} if tab_id else {}
        resp = requests.post(url, headers=self._headers(), json=payload, timeout=60)
        if resp.status_code != 200:
            raise Exception("获取快照失败: %s" % resp.text[:200])
        return resp.json()
    
    def browser_act(self, action: Dict, tab_id: str = None) -> Dict:
        """执行浏览器操作"""
        url = self.base_url + "/browser/act"
        payload = {"action": action}
        if tab_id:
            payload["tabId"] = tab_id
        resp = requests.post(url, headers=self._headers(), json=payload, timeout=30)
        if resp.status_code != 200:
            raise Exception("执行操作失败: %s" % resp.text[:200])
        return resp.json()
    
    def skills_list(self) -> List[Dict]:
        """获取可用技能列表"""
        url = self.base_url + "/skills/list"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=30)
            if resp.status_code == 200:
                return resp.json().get("skills", [])
        except:
            pass
        # 返回硬编码的技能列表（如果 API 不可用）
        return [
            {"id": "pdf", "name": "PDF 处理", "description": "读取、编辑、合并 PDF 文件"},
            {"id": "xlsx", "name": "Excel 表格", "description": "读取、编辑、创建 Excel 文件"},
            {"id": "docx", "name": "Word 文档", "description": "读取、编辑、创建 Word 文档"},
            {"id": "windows-computer-agent", "name": "电脑操作", "description": "自动操作 Windows 电脑"},
            {"id": "online-search", "name": "在线搜索", "description": "搜索互联网获取实时信息"},
        ]
    
    def skill_invoke(self, skill_id: str, params: Dict) -> Dict:
        """调用技能"""
        url = self.base_url + "/skills/invoke"
        payload = {"skillId": skill_id, "params": params}
        resp = requests.post(url, headers=self._headers(), json=payload, timeout=300)
        if resp.status_code != 200:
            raise Exception("技能调用失败: %s" % resp.text[:200])
        return resp.json()
    
    def exec_command(self, command: str, cwd: str = None, timeout: int = 60) -> Dict:
        """执行 Shell 命令"""
        url = self.base_url + "/exec"
        payload = {"command": command, "timeout": timeout}
        if cwd:
            payload["cwd"] = cwd
        resp = requests.post(url, headers=self._headers(), json=payload, timeout=timeout + 10)
        if resp.status_code != 200:
            raise Exception("执行失败: %s" % resp.text[:200])
        return resp.json()


# 全局 API 客户端
API = OpenClawAPI()


# ============================================================
# 记忆管理器
# ============================================================
class MemoryManager:
    """管理 MEMORY.md 和每日日志"""
    
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
        """加载 MEMORY.md"""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    return f.read()
            except:
                return ""
        return ""
    
    def save_memory(self, content: str) -> bool:
        """保存 MEMORY.md"""
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except:
            return False
    
    def append_memory(self, text: str) -> bool:
        """追加到 MEMORY.md"""
        try:
            with open(self.memory_file, "a", encoding="utf-8") as f:
                f.write("\n\n## %s\n\n%s\n" % (datetime.now().strftime('%Y-%m-%d %H:%M'), text))
            return True
        except:
            return False
    
    def load_today_log(self) -> str:
        """加载今日日志"""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.memory_dir / "%s.md" % today
        if log_file.exists():
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    return f.read()
            except:
                return ""
        return ""
    
    def append_today_log(self, text: str) -> bool:
        """追加到今日日志"""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.memory_dir / "%s.md" % today
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write("\n### %s\n\n%s\n" % (datetime.now().strftime('%H:%M:%S'), text))
            return True
        except:
            return False


# 全局记忆管理器
MEMORY = MemoryManager()


# ============================================================
# 截屏功能
# ============================================================
def take_screenshot(target_width=1280, target_height=800):
    """截屏返回 (路径, base64)"""
    from PIL import Image, ImageGrab
    import ctypes
    user32 = ctypes.windll.user32
    w = user32.GetSystemMetrics(0)
    h = user32.GetSystemMetrics(1)
    screenshot = ImageGrab.grab(bbox=(0, 0, w, h))
    screenshot = screenshot.resize((target_width, target_height), Image.LANCZOS)
    
    import tempfile
    out_dir = Path(tempfile.gettempdir()) / "agent_studio"
    out_dir.mkdir(exist_ok=True)
    out_path = str(out_dir / "screen_%d.png" % int(time.time() * 1000))
    screenshot.save(out_path, "PNG")
    
    with open(out_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    
    return out_path, b64


# ============================================================
# 消息气泡
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
            bubble.setStyleSheet("QFrame { background-color: #1f4d7a; border: 1px solid #2d5a8a; border-radius: 12px; }")
            bl = QVBoxLayout(bubble)
            bl.setContentsMargins(12, 10, 12, 10)
            msg = QLabel(text)
            msg.setWordWrap(True)
            msg.setTextFormat(Qt.TextFormat.PlainText)
            msg.setStyleSheet("color: #e1e4e8; font-size: 14px; background: transparent;")
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
            name_label = QLabel("Agent Studio")
            name_label.setStyleSheet("color: #58a6ff; font-size: 12px; font-weight: bold; background: transparent;")
            header.addWidget(name_label)
            if metadata and metadata.get("mode"):
                mode_label = QLabel("[%s]" % metadata["mode"])
                mode_label.setStyleSheet("color: #8b949e; font-size: 11px; background: transparent;")
                header.addWidget(mode_label)
            header.addStretch()
            content_layout.addLayout(header)
            bubble = QFrame()
            bubble.setFrameShape(QFrame.Shape.Box)
            bubble.setLineWidth(0)
            bubble.setStyleSheet("QFrame { background-color: #21262d; border: 1px solid #30363d; border-radius: 12px; }")
            bl = QVBoxLayout(bubble)
            bl.setContentsMargins(12, 10, 12, 10)
            msg = QLabel(text)
            msg.setWordWrap(True)
            msg.setTextFormat(Qt.TextFormat.PlainText)
            msg.setStyleSheet("color: #c9d1d9; font-size: 14px; background: transparent;")
            bl.addWidget(msg)
            if metadata:
                meta_parts = []
                if metadata.get("time_ms"):
                    meta_parts.append("⏱ %dms" % metadata["time_ms"])
                if metadata.get("tokens_completion"):
                    meta_parts.append("📝 %d tokens" % metadata["tokens_completion"])
                if meta_parts:
                    meta_label = QLabel(" | ".join(meta_parts))
                    meta_label.setStyleSheet("color: #6e7681; font-size: 11px; background: transparent; margin-top: 8px;")
                    bl.addWidget(meta_label)
            content_layout.addWidget(bubble)
            main_layout.addLayout(content_layout)
            main_layout.addStretch(3)

        self.setStyleSheet("QFrame { background: transparent; }")


# ============================================================
# 聊天工作线程 - 调 OpenClaw API + 记忆
# ============================================================
class ChatWorker(QThread):
    result_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    progress_update = pyqtSignal(str)

    def __init__(self, task, history=None, memory_context=None):
        super().__init__()
        self.task = task
        self.history = history or []
        self.memory_context = memory_context

    def run(self):
        start_time = time.time()
        try:
            self.progress_update.emit("正在调用 OpenClaw LLM...")

            # 构建系统提示（包含记忆）
            memory_text = self.memory_context or ""
            system_prompt = "你是 Agent Studio，一个全能型AI助手。你可以回答问题、编写代码、分析数据、写作翻译。\n当用户输入操作电脑的请求时，请告诉用户点击「🖱️ 操作电脑」按钮。\n\n"
            if memory_text:
                system_prompt += "## 用户记忆（长期）\n\n%s\n\n请参考以上记忆回答用户问题。\n\n" % memory_text[:2000]
            system_prompt += "请用中文回答。"

            messages = [{"role": "system", "content": system_prompt}]
            for h in self.history[-20:]:
                messages.append({"role": h["role"], "content": h["content"]})
            messages.append({"role": "user", "content": self.task})

            data = API.chat(messages, stream=False)
            answer = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            elapsed = int((time.time() - start_time) * 1000)

            # 保存到今日日志
            MEMORY.append_today_log("**用户**：%s\n\n**助手**：%s\n" % (self.task, answer))

            self.result_ready.emit({
                "success": True,
                "answer": answer,
                "mode": "chat",
                "time_ms": elapsed,
                "tokens_prompt": usage.get("prompt_tokens", 0),
                "tokens_completion": usage.get("completion_tokens", 0),
            })
        except requests.exceptions.Timeout:
            self.error_occurred.emit("请求超时（120秒），请检查 OpenClaw 是否正常运行。")
        except requests.exceptions.ConnectionError:
            self.error_occurred.emit("无法连接 OpenClaw API 服务器，请检查 OpenClaw 是否启动。")
        except Exception as e:
            self.error_occurred.emit("执行出错: %s\n\n%s" % (str(e), traceback.format_exc()[:300]))


# ============================================================
# 电脑操作工作线程 - 截屏+OpenClaw多模态+pywinauto执行
# ============================================================
class ComputerWorker(QThread):
    step_update = pyqtSignal(str)
    result_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    screenshot_ready = pyqtSignal(str)

    def __init__(self, goal, max_steps=20):
        super().__init__()
        self.goal = goal
        self.max_steps = max_steps

    def run(self):
        start_time = time.time()
        try:
            from pywinauto import mouse
            from pywinauto.keyboard import send_keys
            import ctypes

            user32 = ctypes.windll.user32
            screen_w = user32.GetSystemMetrics(0)
            screen_h = user32.GetSystemMetrics(1)
            target_w, target_h = 1280, 800

            system_prompt = (
                "You are a Windows computer operation agent. You see the screen and decide the next action.\n"
                "Screenshot size: %dx%d, real screen: %dx%d\n"
                "Coordinates in screenshot space will be scaled to real screen.\n\n"
                "Available actions (output ONE JSON per turn):\n"
                '{"action":"click","x":640,"y":400} - Left click\n'
                '{"action":"double_click","x":640,"y":400} - Double click\n'
                '{"action":"right_click","x":640,"y":400} - Right click\n'
                '{"action":"type","text":"hello"} - Type text (Chinese supported)\n'
                '{"action":"key","keys":"ctrl+c"} - Keyboard shortcut\n'
                '{"action":"scroll","direction":"down","amount":3} - Scroll\n'
                '{"action":"drag","start_x":100,"start_y":100,"end_x":500,"end_y":500} - Drag\n'
                '{"action":"run_command","command":"notepad"} - Run shell command\n'
                '{"action":"wait","seconds":2} - Wait\n'
                '{"action":"done","reason":"Task completed"} - Task done\n\n'
                "Output ONLY a JSON object. Example:\n"
                '{"thinking":"I see the Start button","action":"click","x":20,"y":780}'
            ) % (target_w, target_h, screen_w, screen_h)

            history = []

            for step in range(1, self.max_steps + 1):
                # 截屏
                self.step_update.emit("Step %d: 截屏..." % step)
                scr_path, scr_b64 = take_screenshot(target_w, target_h)
                self.screenshot_ready.emit(scr_path)

                # 调 OpenClaw 多模态 API
                self.step_update.emit("Step %d: 分析屏幕..." % step)
                messages = [{"role": "system", "content": system_prompt}]
                for h in history[-6:]:
                    messages.append(h)
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Goal: %s\nStep: %d\nNext action?" % (self.goal, step)},
                        {"type": "image_url", "image_url": {"url": "data:image/png;base64,%s" % scr_b64}}
                    ]
                })

                data = API.chat(messages, temperature=0.1, max_tokens=512)
                raw = data["choices"][0]["message"]["content"]
                history.append({"role": "user", "content": "Goal: %s, Step: %d" % (self.goal, step)})
                history.append({"role": "assistant", "content": raw})

                # 解析 JSON
                import re
                action = None
                try:
                    action = json.loads(raw)
                except:
                    m = re.search(r'\{[^{}]*\}', raw, re.DOTALL)
                    if m:
                        try:
                            action = json.loads(m.group())
                        except:
                            pass

                if not action:
                    self.step_update.emit("Step %d: 无法解析操作" % step)
                    continue

                act_name = action.get("action", "")
                thinking = action.get("thinking", "")
                self.step_update.emit("Step %d: %s %s" % (step, act_name, thinking[:50] if thinking else ""))

                # 检查完成
                if act_name == "done":
                    reason = action.get("reason", "任务完成")
                    elapsed = int((time.time() - start_time) * 1000)
                    MEMORY.append_today_log("**电脑操作**：%s\n\n**结果**：✅ %s（%d 步，%dms）\n" % (self.goal, reason, step, elapsed))
                    self.result_ready.emit({
                        "success": True,
                        "answer": "✅ %s\n\n共执行 %d 步，耗时 %dms" % (reason, step, elapsed),
                        "mode": "computer",
                        "time_ms": elapsed,
                        "steps": step,
                    })
                    return

                # 执行操作
                x_ratio = screen_w / target_w
                y_ratio = screen_h / target_h

                try:
                    if act_name in ("click", "double_click", "right_click"):
                        rx = int(action.get("x", 0) * x_ratio)
                        ry = int(action.get("y", 0) * y_ratio)
                        if act_name == "click":
                            mouse.click(coords=(rx, ry))
                        elif act_name == "double_click":
                            mouse.double_click(coords=(rx, ry))
                        elif act_name == "right_click":
                            mouse.right_click(coords=(rx, ry))
                        time.sleep(0.5)

                    elif act_name == "type":
                        text_input = action.get("text", "")
                        has_chinese = any("\u4e00" <= c <= "\u9fff" for c in text_input)
                        if has_chinese:
                            CF_UNICODETEXT = 13
                            kernel32 = ctypes.windll.kernel32
                            user32_ = ctypes.windll.user32
                            kernel32.GlobalAlloc.restype = ctypes.c_void_p
                            kernel32.GlobalLock.restype = ctypes.c_void_p
                            encoded = text_input.encode("utf-16-le") + b"\x00\x00"
                            h_mem = kernel32.GlobalAlloc(0x0042, len(encoded))
                            p_mem = kernel32.GlobalLock(h_mem)
                            ctypes.cdll.msvcrt.memcpy(p_mem, encoded, len(encoded))
                            kernel32.GlobalUnlock(h_mem)
                            user32_.OpenClipboard(0)
                            user32_.EmptyClipboard()
                            user32_.SetClipboardData(CF_UNICODETEXT, h_mem)
                            user32_.CloseClipboard()
                            send_keys("^v")
                        else:
                            escaped = text_input.replace("{", "{{").replace("}", "}}")
                            escaped = escaped.replace("+", "{+}").replace("^", "{^}").replace("%", "{%}")
                            send_keys(escaped, pause=0.012)
                        time.sleep(0.5)

                    elif act_name == "key":
                        keys = action.get("keys", "")
                        key_map = {
                            "ctrl": "^", "alt": "%", "shift": "+",
                            "enter": "{ENTER}", "esc": "{ESC}", "tab": "{TAB}",
                            "backspace": "{BACKSPACE}", "delete": "{DELETE}",
                            "pageup": "{PGUP}", "pagedown": "{PGDN}",
                        }
                        parts = keys.split("+")
                        result_str = ""
                        for p in parts:
                            p = p.strip().lower()
                            result_str += key_map.get(p, p)
                        send_keys(result_str)
                        time.sleep(0.5)

                    elif act_name == "scroll":
                        direction = action.get("direction", "down")
                        amount = action.get("amount", 3)
                        delta = -1 if direction == "down" else 1
                        for _ in range(amount):
                            mouse.scroll(coords=(0, 0), wheel_dist=delta)
                            time.sleep(0.1)

                    elif act_name == "drag":
                        sx = int(action.get("start_x", 0) * x_ratio)
                        sy = int(action.get("start_y", 0) * y_ratio)
                        ex = int(action.get("end_x", 0) * x_ratio)
                        ey = int(action.get("end_y", 0) * y_ratio)
                        mouse.press(coords=(sx, sy))
                        time.sleep(0.2)
                        mouse.move(coords=(ex, ey))
                        time.sleep(0.2)
                        mouse.release(coords=(ex, ey))
                        time.sleep(0.5)

                    elif act_name == "run_command":
                        cmd = action.get("command", "")
                        subprocess.Popen(cmd, shell=True)
                        time.sleep(1)

                    elif act_name == "wait":
                        seconds = action.get("seconds", 2)
                        time.sleep(seconds)

                except Exception as e:
                    self.step_update.emit("Step %d: 执行失败 - %s" % (step, str(e)[:50]))

                time.sleep(1.0)

            elapsed = int((time.time() - start_time) * 1000)
            self.result_ready.emit({
                "success": True,
                "answer": "⚠️ 达到最大步数 (%d)，任务未完成。耗时 %dms" % (self.max_steps, elapsed),
                "mode": "computer",
                "time_ms": elapsed,
                "steps": self.max_steps,
            })

        except Exception as e:
            self.error_occurred.emit("操作出错: %s\n\n%s" % (str(e), traceback.format_exc()[:500]))


# ============================================================
# 浏览器自动化工作线程
# ============================================================
class BrowserWorker(QThread):
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
            if self.action == "open":
                url = self.params.get("url", "https://www.google.com")
                self.progress.emit("正在打开: %s" % url)
                result = API.browser_open(url)
                self.screenshot_ready.emit(result.get("screenshot", ""))
                self.result_ready.emit({"success": True, "message": "页面已打开", "tab_id": result.get("tabId")})
            
            elif self.action == "snapshot":
                self.progress.emit("正在获取页面快照...")
                result = API.browser_snapshot(self.params.get("tab_id"))
                screenshot = result.get("screenshot", "")
                if screenshot:
                    self.screenshot_ready.emit(screenshot)
                self.result_ready.emit({"success": True, "message": "快照已获取", "elements": result.get("elements", [])})
            
            elif self.action == "act":
                self.progress.emit("正在执行操作...")
                result = API.browser_act(self.params.get("action"), self.params.get("tab_id"))
                self.screenshot_ready.emit(result.get("screenshot", ""))
                self.result_ready.emit({"success": True, "message": "操作已完成"})
        
        except Exception as e:
            self.error_occurred.emit(str(e))


# ============================================================
# 技能调用工作线程
# ============================================================
class SkillWorker(QThread):
    progress = pyqtSignal(str)
    result_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, skill_id: str, params: Dict):
        super().__init__()
        self.skill_id = skill_id
        self.params = params

    def run(self):
        try:
            self.progress.emit("正在调用技能: %s" % self.skill_id)
            result = API.skill_invoke(self.skill_id, self.params)
            self.progress.emit("技能执行完成")
            self.result_ready.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))


# ============================================================
# 代码执行工作线程
# ============================================================
class ExecWorker(QThread):
    progress = pyqtSignal(str)
    output_ready = pyqtSignal(str, str)  # stdout, stderr
    error_occurred = pyqtSignal(str)

    def __init__(self, command: str, cwd: str = None, timeout: int = 60):
        super().__init__()
        self.command = command
        self.cwd = cwd
        self.timeout = timeout

    def run(self):
        try:
            self.progress.emit("正在执行命令...")
            result = API.exec_command(self.command, self.cwd, self.timeout)
            stdout = result.get("stdout", "")
            stderr = result.get("stderr", "")
            exit_code = result.get("exit_code", -1)
            
            self.progress.emit("执行完成 (退出码: %d)" % exit_code)
            self.output_ready.emit(stdout, stderr)
            
            # 记录到今日日志
            MEMORY.append_today_log("**执行命令**：`%s`\n\n**结果**：退出码 %d\n" % (self.command, exit_code))
        
        except Exception as e:
            self.error_occurred.emit(str(e))


# ============================================================
# 聊天页面
# ============================================================
class ChatPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.chat_history = []
        self.worker = None
        self.computer_worker = None
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

        model_label = QLabel("🤖 模型:")
        model_label.setStyleSheet("color: #c9d1d9; background: transparent;")
        top_layout.addWidget(model_label)

        self.model_label = QLabel("openclaw (OpenClaw 系统模型)")
        self.model_label.setStyleSheet("color: #58a6ff; background: transparent; font-weight: bold;")
        top_layout.addWidget(self.model_label)

        top_layout.addStretch()

        # 电脑操作按钮
        self.computer_btn = QPushButton("🖱️ 操作电脑")
        self.computer_btn.setFixedSize(120, 36)
        self.computer_btn.setStyleSheet("""
            QPushButton {
                background: #1f6feb; color: white; border: none;
                border-radius: 6px; font-size: 13px; font-weight: bold;
            }
            QPushButton:hover { background: #388bfd; }
            QPushButton:disabled { background: #21262d; color: #484f58; }
        """)
        self.computer_btn.clicked.connect(self.start_computer_mode)
        top_layout.addWidget(self.computer_btn)

        self.status_label = QLabel("✅ 就绪")
        self.status_label.setStyleSheet("color: #3fb950; font-size: 12px; background: transparent; padding: 4px 12px;")
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

        # 步骤显示区
        self.step_label = QLabel("")
        self.step_label.setStyleSheet("color: #d29922; font-size: 12px; background: #161b22; padding: 6px 16px; border-top: 1px solid #30363d;")
        self.step_label.hide()
        layout.addWidget(self.step_label)

        # 输入区域
        input_frame = QFrame()
        input_frame.setFrameShape(QFrame.Shape.NoFrame)
        input_frame.setStyleSheet("QFrame { background: #161b22; border-top: 1px solid #30363d; }")
        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(16, 12, 16, 12)
        input_layout.setSpacing(8)

        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("输入消息，Ctrl+Enter 发送...")
        self.input_field.setMaximumHeight(120)
        self.input_field.setMinimumHeight(50)
        self.input_field.setStyleSheet("""
            QTextEdit {
                background: #0d1117; color: #e6edf3; border: 1px solid #30363d;
                border-radius: 8px; padding: 10px 12px; font-size: 14px;
            }
            QTextEdit:focus { border: 1px solid #388bfd; }
        """)
        input_layout.addWidget(self.input_field)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.clear_btn = QPushButton("🗑️ 清空")
        self.clear_btn.setFixedSize(80, 36)
        self.clear_btn.setStyleSheet("""
            QPushButton { background: #21262d; color: #c9d1d9; border: 1px solid #30363d; border-radius: 6px; font-size: 12px; }
            QPushButton:hover { background: #30363d; }
        """)
        self.clear_btn.clicked.connect(self.clear_chat)
        btn_row.addWidget(self.clear_btn)

        btn_row.addStretch()

        self.send_btn = QPushButton("发送 ➤")
        self.send_btn.setFixedSize(100, 40)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setStyleSheet("""
            QPushButton { background: #238636; color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background: #2ea043; }
            QPushButton:disabled { background: #21262d; color: #484f58; }
        """)
        self.send_btn.clicked.connect(self.send_message)
        btn_row.addWidget(self.send_btn)
        input_layout.addLayout(btn_row)
        layout.addWidget(input_frame)

        # 欢迎消息
        memory_text = MEMORY.load_memory()
        welcome_msg = "你好！我是 Agent Studio V5，完整版。\n\n"
        welcome_msg += "💬 聊天：直接输入问题，我会调用 OpenClaw LLM 回答\n"
        welcome_msg += "🖱️ 操作电脑：点击右上角「操作电脑」按钮\n"
        welcome_msg += "📁 文件管理：点击左侧「文件」图标\n"
        welcome_msg += "📋 任务调度：点击左侧「任务」图标（真实 cron 调度）\n"
        welcome_msg += "🌐 浏览器：点击左侧「浏览器」图标\n"
        welcome_msg += "🔧 技能：点击左侧「技能」图标\n"
        welcome_msg += "💻 代码：点击左侧「代码」图标\n"
        welcome_msg += "🧠 记忆：我会记住重要信息（自动保存到 MEMORY.md）\n\n"
        if memory_text:
            welcome_msg += "✅ 已加载记忆（%d 字节）" % len(memory_text)
        else:
            welcome_msg += "ℹ️ 暂无记忆"
        
        self.add_message(welcome_msg, is_user=False)

    def add_message(self, text, is_user=True, metadata=None):
        bubble = MessageBubble(text, is_user, metadata)
        self.message_layout.insertWidget(self.message_layout.count() - 1, bubble)
        sb = self.scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    def set_busy(self, busy):
        self.send_btn.setEnabled(not busy)
        self.clear_btn.setEnabled(not busy)
        self.computer_btn.setEnabled(not busy)
        if busy:
            self.status_label.setText("⏳ 执行中...")
            self.status_label.setStyleSheet("color: #d29922; font-size: 12px; background: transparent;")
        else:
            self.status_label.setText("✅ 就绪")
            self.status_label.setStyleSheet("color: #3fb950; font-size: 12px; background: transparent;")

    def send_message(self):
        text = self.input_field.toPlainText().strip()
        if not text:
            return
        self.add_message(text, is_user=True)
        self.input_field.clear()
        self.set_busy(True)

        memory_text = MEMORY.load_memory()
        memory_context = memory_text[:2000] if memory_text else None

        self.worker = ChatWorker(text, self.chat_history, memory_context)
        self.worker.result_ready.connect(self.on_chat_result)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.progress_update.connect(lambda m: self.status_label.setText("⏳ %s" % m))
        self.worker.start()

    def start_computer_mode(self):
        text = self.input_field.toPlainText().strip()
        if not text:
            self.add_message("请先在输入框写下你要执行的操作目标，再点击「操作电脑」。", is_user=False)
            return
        self.add_message(text, is_user=True)
        self.add_message("🖱️ 开始接管电脑，目标：%s\n请不要动鼠标和键盘..." % text, is_user=False)
        self.input_field.clear()
        self.set_busy(True)
        self.step_label.show()
        self.step_label.setText("正在启动...")

        self.computer_worker = ComputerWorker(text, max_steps=20)
        self.computer_worker.step_update.connect(lambda m: self.step_label.setText(m))
        self.computer_worker.result_ready.connect(self.on_computer_result)
        self.computer_worker.error_occurred.connect(self.on_error)
        self.computer_worker.start()

    def on_chat_result(self, result):
        metadata = {"mode": result.get("mode", "chat"), "time_ms": result.get("time_ms", 0), "tokens_completion": result.get("tokens_completion", 0)}
        self.add_message(result["answer"], is_user=False, metadata=metadata)
        self.chat_history.append({"role": "user", "content": self.worker.task})
        self.chat_history.append({"role": "assistant", "content": result["answer"]})
        self.set_busy(False)

    def on_computer_result(self, result):
        self.step_label.hide()
        self.add_message(result["answer"], is_user=False, metadata={"mode": "computer", "time_ms": result.get("time_ms", 0), "steps": result.get("steps", 0)})
        self.set_busy(False)

    def on_error(self, msg):
        self.step_label.hide()
        self.add_message("❌ %s" % msg, is_user=False)
        self.set_busy(False)

    def clear_chat(self):
        while self.message_layout.count() > 1:
            item = self.message_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.chat_history = []
        self.add_message("对话已清空。", is_user=False)


# ============================================================
# 文件管理页面
# ============================================================
class FilesPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_file = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("📁 文件管理")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #e6edf3; background: transparent;")
        layout.addWidget(title)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        left_panel = QFrame()
        left_panel.setStyleSheet("QFrame { background: #161b22; border: 1px solid #30363d; border-radius: 8px; }")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 8, 8, 8)
        
        self.dir_tree = QTreeWidget()
        self.dir_tree.setHeaderLabel("目录")
        self.dir_tree.setStyleSheet("""
            QTreeWidget { background: #0d1117; color: #c9d1d9; border: none; }
            QTreeWidget::item { padding: 4px; }
            QTreeWidget::item:selected { background: #1f6feb; color: white; }
        """)
        self.dir_tree.itemDoubleClicked.connect(self.on_file_double_clicked)
        left_layout.addWidget(self.dir_tree)

        btn_row = QHBoxLayout()
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setStyleSheet("QPushButton { background: #21262d; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px; padding: 4px 12px; }")
        refresh_btn.clicked.connect(self.refresh_tree)
        btn_row.addWidget(refresh_btn)
        
        open_btn = QPushButton("📂 打开目录")
        open_btn.setStyleSheet("QPushButton { background: #21262d; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px; padding: 4px 12px; }")
        open_btn.clicked.connect(self.open_directory)
        btn_row.addWidget(open_btn)
        
        left_layout.addLayout(btn_row)
        splitter.addWidget(left_panel)
        
        right_panel = QFrame()
        right_panel.setStyleSheet("QFrame { background: #161b22; border: 1px solid #30363d; border-radius: 8px; }")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 8, 8, 8)
        
        self.file_path_label = QLabel("未打开文件")
        self.file_path_label.setStyleSheet("color: #8b949e; background: transparent; font-size: 12px;")
        right_layout.addWidget(self.file_path_label)
        
        self.file_editor = QTextEdit()
        self.file_editor.setStyleSheet("""
            QTextEdit { background: #0d1117; color: #e6edf3; border: 1px solid #30363d; border-radius: 6px; padding: 8px; font-family: 'Consolas', 'Courier New', monospace; font-size: 13px; }
        """)
        right_layout.addWidget(self.file_editor)
        
        save_btn = QPushButton("💾 保存")
        save_btn.setStyleSheet("QPushButton { background: #238636; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-weight: bold; } QPushButton:hover { background: #2ea043; }")
        save_btn.clicked.connect(self.save_file)
        right_layout.addWidget(save_btn)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 700])
        layout.addWidget(splitter)
        
        self.current_dir = Path.home()
        self.refresh_tree()

    def refresh_tree(self):
        self.dir_tree.clear()
        root = QTreeWidgetItem(self.dir_tree, [str(self.current_dir)])
        root.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_DirIcon))
        self.load_directory(root, self.current_dir)
        root.setExpanded(True)

    def load_directory(self, parent_item, directory):
        try:
            for item in sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                if item.name.startswith('.'):
                    continue
                tree_item = QTreeWidgetItem(parent_item, [item.name])
                if item.is_dir():
                    tree_item.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_DirIcon))
                    if parent_item == self.dir_tree.topLevelItem(0):
                        self.load_directory(tree_item, item)
                else:
                    tree_item.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_FileIcon))
                    tree_item.setData(0, Qt.ItemDataRole.UserRole, str(item))
        except PermissionError:
            pass

    def open_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择目录", str(self.current_dir))
        if dir_path:
            self.current_dir = Path(dir_path)
            self.refresh_tree()

    def on_file_double_clicked(self, item, column):
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.file_editor.setPlainText(content)
                self.file_path_label.setText(str(file_path))
                self.current_file = Path(file_path)
            except Exception as e:
                QMessageBox.critical(self, "错误", "无法读取文件: %s" % str(e))

    def save_file(self):
        if not self.current_file:
            QMessageBox.warning(self, "警告", "请先打开一个文件！")
            return
        try:
            content = self.file_editor.toPlainText()
            with open(self.current_file, "w", encoding="utf-8") as f:
                f.write(content)
            QMessageBox.information(self, "成功", "文件已保存！")
            MEMORY.append_today_log("**文件编辑**：%s\n" % self.current_file)
        except Exception as e:
            QMessageBox.critical(self, "错误", "保存失败: %s" % str(e))


# ============================================================
# 任务调度页面 - 真实 OpenClaw Cron API
# ============================================================
class TasksPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_tasks()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("📋 任务调度（OpenClaw Cron API）")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #e6edf3; background: transparent;")
        layout.addWidget(title)

        # 新建任务
        new_box = QGroupBox("新建定时任务")
        new_box.setStyleSheet("QGroupBox { color: #e6edf3; border: 1px solid #30363d; border-radius: 8px; margin-top: 10px; font-weight: bold; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        new_layout = QFormLayout(new_box)
        new_layout.setSpacing(12)

        self.task_name_input = QLineEdit()
        self.task_name_input.setPlaceholderText("任务名称")
        self.task_name_input.setStyleSheet("QLineEdit { background: #0d1117; color: #e6edf3; border: 1px solid #30363d; border-radius: 6px; padding: 8px; }")
        new_layout.addRow("名称:", self.task_name_input)

        self.task_message_input = QTextEdit()
        self.task_message_input.setPlaceholderText("任务内容（发送给 AI 的消息）")
        self.task_message_input.setMaximumHeight(80)
        self.task_message_input.setStyleSheet("QTextEdit { background: #0d1117; color: #e6edf3; border: 1px solid #30363d; border-radius: 6px; padding: 8px; }")
        new_layout.addRow("内容:", self.task_message_input)

        # 调度类型
        schedule_row = QHBoxLayout()
        self.schedule_type = QComboBox()
        self.schedule_type.addItems(["一次性 (at)", "周期性 (every)", "Cron 表达式"])
        self.schedule_type.currentIndexChanged.connect(self.on_schedule_type_changed)
        self.schedule_type.setStyleSheet("QComboBox { background: #0d1117; color: #e6edf3; border: 1px solid #30363d; border-radius: 6px; padding: 6px; }")
        schedule_row.addWidget(self.schedule_type)
        
        self.schedule_detail = QLineEdit()
        self.schedule_detail.setPlaceholderText("2026-06-05T10:00:00")
        self.schedule_detail.setStyleSheet("QLineEdit { background: #0d1117; color: #e6edf3; border: 1px solid #30363d; border-radius: 6px; padding: 6px; }")
        schedule_row.addWidget(self.schedule_detail)
        new_layout.addRow("调度:", schedule_row)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        add_btn = QPushButton("➕ 添加任务")
        add_btn.setStyleSheet("QPushButton { background: #238636; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-weight: bold; } QPushButton:hover { background: #2ea043; }")
        add_btn.clicked.connect(self.add_task)
        btn_row.addWidget(add_btn)
        new_layout.addRow(btn_row)
        layout.addWidget(new_box)

        # 任务列表
        list_box = QGroupBox("任务列表")
        list_box.setStyleSheet("QGroupBox { color: #e6edf3; border: 1px solid #30363d; border-radius: 8px; margin-top: 10px; font-weight: bold; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        list_layout = QVBoxLayout(list_box)
        
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(5)
        self.task_table.setHorizontalHeaderLabels(["任务名", "内容", "调度", "状态", "操作"])
        self.task_table.horizontalHeader().setStretchLastSection(False)
        self.task_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.task_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.task_table.setColumnWidth(2, 150)
        self.task_table.setColumnWidth(3, 80)
        self.task_table.setColumnWidth(4, 100)
        self.task_table.setStyleSheet("QTableWidget { background: #0d1117; color: #e6edf3; border: none; gridline-color: #30363d; } QHeaderView::section { background: #161b22; color: #e6edf3; padding: 8px; border: 1px solid #30363d; font-weight: bold; }")
        list_layout.addWidget(self.task_table)
        layout.addWidget(list_box)

        # 刷新按钮
        refresh_row = QHBoxLayout()
        refresh_row.addStretch()
        refresh_btn = QPushButton("🔄 刷新列表")
        refresh_btn.setStyleSheet("QPushButton { background: #1f6feb; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-weight: bold; } QPushButton:hover { background: #388bfd; }")
        refresh_btn.clicked.connect(self.load_tasks)
        refresh_row.addWidget(refresh_btn)
        layout.addLayout(refresh_row)

    def on_schedule_type_changed(self, index):
        placeholders = ["2026-06-05T10:00:00", "3600000 (毫秒)", "0 9 * * *"]
        self.schedule_detail.setPlaceholderText(placeholders[index])

    def add_task(self):
        name = self.task_name_input.text().strip()
        message = self.task_message_input.toPlainText().strip()
        schedule_str = self.schedule_detail.text().strip()
        
        if not name or not message or not schedule_str:
            QMessageBox.warning(self, "警告", "请填写完整信息！")
            return
        
        try:
            schedule_type = self.schedule_type.currentIndex()
            
            if schedule_type == 0:  # at
                schedule = {"kind": "at", "at": schedule_str}
            elif schedule_type == 1:  # every
                schedule = {"kind": "every", "everyMs": int(schedule_str)}
            else:  # cron
                schedule = {"kind": "cron", "expr": schedule_str}
            
            job = {
                "name": name,
                "schedule": schedule,
                "payload": {
                    "kind": "agentTurn",
                    "message": message
                },
                "enabled": True
            }
            
            result = API.cron_add(job)
            self.task_name_input.clear()
            self.task_message_input.clear()
            self.load_tasks()
            
            MEMORY.append_today_log("**新建定时任务**：%s\n" % name)
            QMessageBox.information(self, "成功", "任务已添加！")
        
        except Exception as e:
            QMessageBox.critical(self, "错误", "添加失败: %s" % str(e))

    def load_tasks(self):
        try:
            jobs = API.cron_list()
            self.task_table.setRowCount(len(jobs))
            
            for i, job in enumerate(jobs):
                self.task_table.setItem(i, 0, QTableWidgetItem(job.get("name", "")))
                self.task_table.setItem(i, 1, QTableWidgetItem(job.get("payload", {}).get("message", "")[:50]))
                
                schedule = job.get("schedule", {})
                schedule_text = json.dumps(schedule)
                self.task_table.setItem(i, 2, QTableWidgetItem(schedule_text))
                
                status = "启用" if job.get("enabled", True) else "禁用"
                status_item = QTableWidgetItem(status)
                if job.get("enabled", True):
                    status_item.setForeground(QColor("#3fb950"))
                else:
                    status_item.setForeground(QColor("#8b949e"))
                self.task_table.setItem(i, 3, status_item)
                
                # 操作按钮
                btn_widget = QWidget()
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(4, 4, 4, 4)
                btn_layout.setSpacing(4)
                
                delete_btn = QPushButton("🗑️")
                delete_btn.setStyleSheet("background: transparent; border: none; font-size: 14px;")
                delete_btn.clicked.connect(lambda checked, jid=job.get("jobId"): self.delete_task(jid))
                btn_layout.addWidget(delete_btn)
                
                self.task_table.setCellWidget(i, 4, btn_widget)
        
        except Exception as e:
            print("加载任务失败: %s" % str(e))

    def delete_task(self, job_id):
        try:
            API.cron_remove(job_id)
            self.load_tasks()
            MEMORY.append_today_log("**删除定时任务**：%s\n" % job_id)
        except Exception as e:
            QMessageBox.critical(self, "错误", "删除失败: %s" % str(e))


# ============================================================
# 浏览器自动化页面
# ============================================================
class BrowserPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_tab_id = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("🌐 浏览器自动化")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #e6edf3; background: transparent;")
        layout.addWidget(title)

        # URL 输入
        url_row = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("输入网址...")
        self.url_input.setStyleSheet("QLineEdit { background: #0d1117; color: #e6edf3; border: 1px solid #30363d; border-radius: 6px; padding: 8px; }")
        url_row.addWidget(self.url_input, stretch=1)

        go_btn = QPushButton("打开")
        go_btn.setStyleSheet("QPushButton { background: #238636; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-weight: bold; } QPushButton:hover { background: #2ea043; }")
        go_btn.clicked.connect(self.open_url)
        url_row.addWidget(go_btn)
        layout.addLayout(url_row)

        # 截图显示
        self.screenshot_label = QLabel()
        self.screenshot_label.setMinimumHeight(400)
        self.screenshot_label.setStyleSheet("QLabel { background: #161b22; border: 1px solid #30363d; border-radius: 8px; }")
        self.screenshot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.screenshot_label.setText("截图将显示在这里")
        layout.addWidget(self.screenshot_label)

        # 操作区
        action_box = QGroupBox("操作")
        action_box.setStyleSheet("QGroupBox { color: #e6edf3; border: 1px solid #30363d; border-radius: 8px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        action_layout = QHBoxLayout(action_box)
        
        action_row1 = QHBoxLayout()
        action_row1.addWidget(QLabel("类型:"))
        self.action_type = QComboBox()
        self.action_type.addItems(["click", "type", "key", "scroll"])
        self.action_type.setStyleSheet("QComboBox { background: #0d1117; color: #e6edf3; border: 1px solid #30363d; border-radius: 6px; padding: 6px; }")
        action_row1.addWidget(self.action_type)
        action_layout.addLayout(action_row1)

        action_row2 = QHBoxLayout()
        action_row2.addWidget(QLabel("参数:"))
        self.action_params = QLineEdit()
        self.action_params.setPlaceholderText("x=100,y=200 或 text=hello")
        self.action_params.setStyleSheet("QLineEdit { background: #0d1117; color: #e6edf3; border: 1px solid #30363d; border-radius: 6px; padding: 6px; }")
        action_row2.addWidget(self.action_params)
        action_layout.addLayout(action2)

        exec_btn = QPushButton("执行")
        exec_btn.setStyleSheet("QPushButton { background: #1f6feb; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-weight: bold; } QPushButton:hover { background: #388bfd; }")
        exec_btn.clicked.connect(self.execute_action)
        action_layout.addWidget(exec_btn)

        snapshot_btn = QPushButton("📷 截图")
        snapshot_btn.setStyleSheet("QPushButton { background: #21262d; color: #c9d1d9; border: 1px solid #30363d; border-radius: 6px; padding: 8px 20px; } QPushButton:hover { background: #30363d; }")
        snapshot_btn.clicked.connect(self.take_snapshot)
        action_layout.addWidget(snapshot_btn)

        layout.addWidget(action_box)

        # 状态
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #8b949e; background: transparent;")
        layout.addWidget(self.status_label)

    def open_url(self):
        url = self.url_input.text().strip()
        if not url:
            return
        if not url.startswith("http"):
            url = "https://" + url
        
        self.status_label.setText("正在打开 %s..." % url)
        
        self.worker = BrowserWorker("open", {"url": url})
        self.worker.progress.connect(lambda m: self.status_label.setText(m))
        self.worker.screenshot_ready.connect(self.update_screenshot)
        self.worker.result_ready.connect(self.on_result)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.start()

    def take_snapshot(self):
        self.status_label.setText("正在获取快照...")
        
        self.worker = BrowserWorker("snapshot", {"tab_id": self.current_tab_id})
        self.worker.progress.connect(lambda m: self.status_label.setText(m))
        self.worker.screenshot_ready.connect(self.update_screenshot)
        self.worker.result_ready.connect(self.on_result)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.start()

    def execute_action(self):
        action_type = self.action_type.currentText()
        params_str = self.action_params.text().strip()
        
        # 解析参数
        action = {"kind": action_type}
        for part in params_str.split(","):
            if "=" in part:
                k, v = part.split("=", 1)
                k = k.strip()
                v = v.strip()
                if k in ("x", "y", "width", "height", "timeMs", "deltaX", "deltaY"):
                    action[k] = int(v)
                elif k == "text":
                    action["text"] = v
                elif k == "keys":
                    action["keys"] = [k.strip() for k in v.split("+")]
        
        self.status_label.setText("正在执行操作...")
        
        self.worker = BrowserWorker("act", {"action": action, "tab_id": self.current_tab_id})
        self.worker.progress.connect(lambda m: self.status_label.setText(m))
        self.worker.screenshot_ready.connect(self.update_screenshot)
        self.worker.result_ready.connect(self.on_result)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.start()

    def update_screenshot(self, screenshot_path):
        if screenshot_path and Path(screenshot_path).exists():
            from PyQt6.QtGui import QPixmap
            pixmap = QPixmap(screenshot_path)
            self.screenshot_label.setPixmap(pixmap.scaled(
                self.screenshot_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))

    def on_result(self, result):
        self.current_tab_id = result.get("tab_id", self.current_tab_id)
        self.status_label.setText(result.get("message", "完成"))

    def on_error(self, msg):
        self.status_label.setText("❌ %s" % msg)


# ============================================================
# 技能调用页面
# ============================================================
class SkillsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.skills = []
        self.init_ui()
        self.load_skills()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("🔧 技能调用")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #e6edf3; background: transparent;")
        layout.addWidget(title)

        # 技能列表
        list_box = QGroupBox("可用技能")
        list_box.setStyleSheet("QGroupBox { color: #e6edf3; border: 1px solid #30363d; border-radius: 8px; margin-top: 10px; font-weight: bold; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        list_layout = QVBoxLayout(list_box)
        
        self.skill_table = QTableWidget()
        self.skill_table.setColumnCount(3)
        self.skill_table.setHorizontalHeaderLabels(["技能", "描述", "操作"])
        self.skill_table.horizontalHeader().setStretchLastSection(False)
        self.skill_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.skill_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.skill_table.setColumnWidth(2, 80)
        self.skill_table.setStyleSheet("QTableWidget { background: #0d1117; color: #e6edf3; border: none; gridline-color: #30363d; } QHeaderView::section { background: #161b22; color: #e6edf3; padding: 8px; border: 1px solid #30363d; font-weight: bold; }")
        list_layout.addWidget(self.skill_table)
        layout.addWidget(list_box)

        # 参数输入
        param_box = QGroupBox("调用参数")
        param_box.setStyleSheet("QGroupBox { color: #e6edf3; border: 1px solid #30363d; border-radius: 8px; margin-top: 10px; font-weight: bold; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        param_layout = QVBoxLayout(param_box)
        
        self.param_input = QTextEdit()
        self.param_input.setPlaceholderText("输入 JSON 格式的参数...\n例如：{\"input\": \"test.pdf\"}")
        self.param_input.setMaximumHeight(100)
        self.param_input.setStyleSheet("QTextEdit { background: #0d1117; color: #e6edf3; border: 1px solid #30363d; border-radius: 6px; padding: 8px; font-family: 'Consolas', monospace; }")
        param_layout.addWidget(self.param_input)
        
        invoke_btn = QPushButton("▶️ 调用")
        invoke_btn.setStyleSheet("QPushButton { background: #238636; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-weight: bold; } QPushButton:hover { background: #2ea043; }")
        invoke_btn.clicked.connect(self.invoke_selected_skill)
        param_layout.addWidget(invoke_btn)
        layout.addWidget(param_box)

        # 结果显示
        result_box = QGroupBox("执行结果")
        result_box.setStyleSheet("QGroupBox { color: #e6edf3; border: 1px solid #30363d; border-radius: 8px; margin-top: 10px; font-weight: bold; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        result_layout = QVBoxLayout(result_box)
        
        self.result_output = QTextEdit()
        self.result_output.setReadOnly(True)
        self.result_output.setMinimumHeight(150)
        self.result_output.setStyleSheet("QTextEdit { background: #0d1117; color: #e6edf3; border: 1px solid #30363d; border-radius: 6px; padding: 8px; font-family: 'Consolas', monospace; }")
        result_layout.addWidget(self.result_output)
        layout.addWidget(result_box)

        self.current_skill_id = None

    def load_skills(self):
        self.skills = API.skills_list()
        self.skill_table.setRowCount(len(self.skills))
        
        for i, skill in enumerate(self.skills):
            self.skill_table.setItem(i, 0, QTableWidgetItem(skill.get("name", skill.get("id", ""))))
            self.skill_table.setItem(i, 1, QTableWidgetItem(skill.get("description", "")))
            
            select_btn = QPushButton("选择")
            select_btn.setStyleSheet("background: transparent; border: 1px solid #30363d; border-radius: 4px; padding: 4px;")
            select_btn.clicked.connect(lambda checked, sid=skill.get("id"): self.select_skill(sid))
            self.skill_table.setCellWidget(i, 2, select_btn)

    def select_skill(self, skill_id):
        self.current_skill_id = skill_id
        skill = next((s for s in self.skills if s.get("id") == skill_id), None)
        if skill:
            self.result_output.setPlainText("已选择: %s\n\n描述: %s\n\n请输入参数后点击「调用」" % (skill.get("name"), skill.get("description")))

    def invoke_selected_skill(self):
        if not self.current_skill_id:
            QMessageBox.warning(self, "警告", "请先选择一个技能！")
            return
        
        param_text = self.param_input.toPlainText().strip()
        try:
            params = json.loads(param_text) if param_text else {}
        except:
            QMessageBox.critical(self, "错误", "参数格式错误，请输入有效的 JSON！")
            return
        
        self.result_output.setPlainText("正在调用 %s..." % self.current_skill_id)
        
        self.worker = SkillWorker(self.current_skill_id, params)
        self.worker.progress.connect(lambda m: self.result_output.setPlainText(m))
        self.worker.result_ready.connect(lambda r: self.result_output.setPlainText(json.dumps(r, ensure_ascii=False, indent=2)))
        self.worker.error_occurred.connect(lambda e: self.result_output.setPlainText("❌ %s" % e))
        self.worker.start()


# ============================================================
# 代码执行页面
# ============================================================
class CodePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("💻 代码执行")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #e6edf3; background: transparent;")
        layout.addWidget(title)

        # 工作目录
        cwd_row = QHBoxLayout()
        cwd_row.addWidget(QLabel("工作目录:"))
        self.cwd_input = QLineEdit()
        self.cwd_input.setPlaceholderText(str(Path.home()))
        self.cwd_input.setStyleSheet("QLineEdit { background: #0d1117; color: #e6edf3; border: 1px solid #30363d; border-radius: 6px; padding: 8px; }")
        cwd_row.addWidget(self.cwd_input)
        
        browse_btn = QPushButton("📂")
        browse_btn.setStyleSheet("QPushButton { background: #21262d; color: #c9d1d9; border: 1px solid #30363d; border-radius: 6px; padding: 8px; }")
        browse_btn.clicked.connect(self.browse_dir)
        cwd_row.addWidget(browse_btn)
        layout.addLayout(cwd_row)

        # 代码编辑器
        self.code_editor = QPlainTextEdit()
        self.code_editor.setPlaceholderText("输入 Shell 命令或 Python 代码...\n\n示例:\n  pip list\n  python --version\n  echo 'Hello World'")
        self.code_editor.setStyleSheet("QPlainTextEdit { background: #0d1117; color: #e6edf3; border: 1px solid #30363d; border-radius: 6px; padding: 12px; font-family: 'Consolas', 'Courier New', monospace; font-size: 13px; }")
        layout.addWidget(self.code_editor, stretch=1)

        # 超时设置
        timeout_row = QHBoxLayout()
        timeout_row.addWidget(QLabel("超时(秒):"))
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(10, 300)
        self.timeout_spin.setValue(60)
        self.timeout_spin.setStyleSheet("QSpinBox { background: #0d1117; color: #e6edf3; border: 1px solid #30363d; border-radius: 6px; padding: 6px; }")
        timeout_row.addWidget(self.timeout_spin)
        timeout_row.addStretch()
        
        run_btn = QPushButton("▶️ 执行")
        run_btn.setStyleSheet("QPushButton { background: #238636; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-weight: bold; } QPushButton:hover { background: #2ea043; }")
        run_btn.clicked.connect(self.execute_code)
        timeout_row.addWidget(run_btn)
        layout.addLayout(timeout_row)

        # 输出区
        output_box = QGroupBox("输出")
        output_box.setStyleSheet("QGroupBox { color: #e6edf3; border: 1px solid #30363d; border-radius: 8px; margin-top: 10px; font-weight: bold; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        output_layout = QVBoxLayout(output_box)
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet("QTextEdit { background: #0d1117; color: #e6edf3; border: 1px solid #30363d; border-radius: 6px; padding: 8px; font-family: 'Consolas', monospace; }")
        output_layout.addWidget(self.output_text)
        layout.addWidget(output_box)

    def browse_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择工作目录")
        if dir_path:
            self.cwd_input.setText(dir_path)

    def execute_code(self):
        command = self.code_editor.toPlainText().strip()
        if not command:
            return
        
        cwd = self.cwd_input.text().strip() or None
        timeout = self.timeout_spin.value()
        
        self.output_text.setPlainText("正在执行...\n")
        
        self.worker = ExecWorker(command, cwd, timeout)
        self.worker.progress.connect(lambda m: self.output_text.append(m))
        self.worker.output_ready.connect(self.on_output)
        self.worker.error_occurred.connect(lambda e: self.output_text.append("❌ %s" % e))
        self.worker.start()

    def on_output(self, stdout, stderr):
        if stdout:
            self.output_text.append("=== STDOUT ===\n%s" % stdout)
        if stderr:
            self.output_text.append("=== STDERR ===\n%s" % stderr)


# ============================================================
# 统计页面
# ============================================================
class StatsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.stats_file = Path(__file__).parent.parent / "data" / "stats.json"
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("📊 使用统计")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #e6edf3; background: transparent;")
        layout.addWidget(title)

        cards = QHBoxLayout()
        cards.setSpacing(16)
        self.card_calls = self._card("总调用", "0", "🤖", "#58a6ff")
        self.card_tokens = self._card("总Token", "0", "📝", "#a371f7")
        self.card_avg = self._card("平均响应", "0ms", "⏱️", "#3fb950")
        cards.addWidget(self.card_calls)
        cards.addWidget(self.card_tokens)
        cards.addWidget(self.card_avg)
        layout.addLayout(cards)

        self.detail_label = QLabel("加载中...")
        self.detail_label.setStyleSheet("color: #8b949e; background: transparent; line-height: 1.8;")
        layout.addWidget(self.detail_label)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setStyleSheet("QPushButton { background: #1f6feb; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-weight: bold; } QPushButton:hover { background: #388bfd; }")
        refresh_btn.clicked.connect(self.load_stats)
        btn_row.addWidget(refresh_btn)
        layout.addLayout(btn_row)
        layout.addStretch()
        self.load_stats()

    def _card(self, title, value, icon, color):
        card = QFrame()
        card.setStyleSheet("QFrame { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 16px; }")
        layout = QVBoxLayout(card)
        layout.addWidget(QLabel(icon))
        layout.addWidget(QLabel(title))
        val = QLabel(value)
        val.setStyleSheet("color: %s; font-size: 28px; font-weight: bold; background: transparent;" % color)
        val.setObjectName("value_label")
        layout.addWidget(val)
        return card

    def load_stats(self):
        try:
            if self.stats_file.exists():
                with open(self.stats_file, "r", encoding="utf-8") as f:
                    stats = json.load(f)
            else:
                stats = {"calls": 0, "tokens": 0, "total_ms": 0}
            calls = stats.get("calls", 0)
            tokens = stats.get("tokens", 0)
            total_ms = stats.get("total_ms", 0)
            avg = total_ms / calls if calls > 0 else 0
            self.detail_label.setText("总调用: %d\n总Token: %d\n平均响应: %.0fms" % (calls, tokens, avg))
        except:
            self.detail_label.setText("无数据")


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

        api_box = QGroupBox("OpenClaw API 配置")
        api_box.setStyleSheet("QGroupBox { color: #e6edf3; border: 1px solid #30363d; border-radius: 8px; margin-top: 10px; font-weight: bold; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        api_layout = QFormLayout(api_box)
        api_layout.setSpacing(12)

        self.api_url_input = QLineEdit()
        self.api_url_input.setText(CONFIG.get("OPENCLAW_API_URL", ""))
        self.api_url_input.setStyleSheet("QLineEdit { background: #0d1117; color: #e6edf3; border: 1px solid #30363d; border-radius: 6px; padding: 8px; }")
        api_layout.addRow("API URL:", self.api_url_input)

        self.auth_token_input = QLineEdit()
        self.auth_token_input.setPlaceholderText("输入 OpenClaw Auth Token...")
        self.auth_token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.auth_token_input.setStyleSheet("QLineEdit { background: #0d1117; color: #e6edf3; border: 1px solid #30363d; border-radius: 6px; padding: 8px; }")
        api_layout.addRow("Auth Token:", self.auth_token_input)

        self.show_token_check = QCheckBox("显示 Token")
        self.show_token_check.setStyleSheet("color: #c9d1d9; background: transparent;")
        self.show_token_check.stateChanged.connect(lambda s: self.auth_token_input.setEchoMode(
            QLineEdit.EchoMode.Normal if s == Qt.CheckState.Checked.value else QLineEdit.EchoMode.Password
        ))
        api_layout.addRow(self.show_token_check)

        save_btn = QPushButton("💾 保存配置")
        save_btn.setStyleSheet("QPushButton { background: #238636; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-weight: bold; } QPushButton:hover { background: #2ea043; }")
        save_btn.clicked.connect(self.save_settings)
        api_layout.addRow(save_btn)
        layout.addWidget(api_box)

        about_box = QGroupBox("关于")
        about_box.setStyleSheet("QGroupBox { color: #e6edf3; border: 1px solid #30363d; border-radius: 8px; margin-top: 10px; font-weight: bold; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        about_layout = QVBoxLayout(about_box)
        about_text = QLabel(
            "Agent Studio V5 完整版\n\n"
            "✅ 聊天 - OpenClaw LLM\n"
            "✅ 电脑操作 - 截屏+多模态+pywinauto\n"
            "✅ 文件管理 - 本地文件浏览编辑\n"
            "✅ 任务调度 - OpenClaw Cron API\n"
            "✅ 浏览器自动化 - OpenClaw Browser API\n"
            "✅ 技能调用 - OpenClaw Skills API\n"
            "✅ 代码执行 - OpenClaw Exec API\n"
            "✅ 记忆系统 - MEMORY.md\n\n"
            "依赖: PyQt6 + requests + pywinauto + Pillow"
        )
        about_text.setStyleSheet("color: #8b949e; background: transparent; line-height: 1.6;")
        about_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_layout.addWidget(about_text)
        layout.addWidget(about_box)
        layout.addStretch()

    def save_settings(self):
        global CONFIG, API
        api_url = self.api_url_input.text()
        auth_token = self.auth_token_input.text()
        
        config_path = Path.home() / ".qclaw" / "agent_studio_config.json"
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump({
                    "OPENCLAW_API_URL": api_url,
                    "OPENCLAW_AUTH_TOKEN": auth_token,
                    "OPENCLAW_BASE_URL": api_url.replace("/v1/chat/completions", "").replace("/chat/completions", "")
                }, f, ensure_ascii=False, indent=2)
            
            CONFIG["OPENCLAW_API_URL"] = api_url
            CONFIG["OPENCLAW_AUTH_TOKEN"] = auth_token
            CONFIG["OPENCLAW_BASE_URL"] = api_url.replace("/v1/chat/completions", "").replace("/chat/completions", "")
            
            # 更新 API 客户端
            API.base_url = CONFIG["OPENCLAW_BASE_URL"]
            API.token = auth_token
            
            QMessageBox.information(self, "成功", "配置已保存！立即生效。")
        except Exception as e:
            QMessageBox.critical(self, "错误", "保存失败: %s" % str(e))

    def load_settings(self):
        config_path = Path.home() / ".qclaw" / "agent_studio_config.json"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.api_url_input.setText(data.get("OPENCLAW_API_URL", ""))
                    self.auth_token_input.setText(data.get("OPENCLAW_AUTH_TOKEN", ""))
        except:
            pass


# ============================================================
# 侧边栏 + 主窗口
# ============================================================
class SideBar(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(64)
        self.setSpacing(6)
        self.setStyleSheet("""
            QListWidget { background: #010409; border: none; padding: 12px 4px; }
            QListWidget::item { padding: 12px 0; border-radius: 8px; color: #484f58; font-size: 24px; text-align: center; }
            QListWidget::item:selected { background: #161b22; color: #58a6ff; border: 1px solid #30363d; }
            QListWidget::item:hover:!selected { background: #0d1117; color: #8b949e; }
        """)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Agent Studio V5 - 智能体工作室（完整版）")
        self.setGeometry(80, 80, 1280, 850)
        self.setMinimumSize(800, 600)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = SideBar()
        icons = ["💬", "📁", "📋", "🌐", "🔧", "💻", "📊", "⚙️"]
        tooltips = ["聊天", "文件", "任务", "浏览器", "技能", "代码", "统计", "设置"]
        for icon, tooltip in zip(icons, tooltips):
            item = QListWidgetItem(icon)
            item.setSizeHint(QSize(56, 50))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setToolTip(tooltip)
            self.sidebar.addItem(item)
        self.sidebar.setCurrentRow(0)
        root.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.chat_page = ChatPage()
        self.files_page = FilesPage()
        self.tasks_page = TasksPage()
        self.browser_page = BrowserPage()
        self.skills_page = SkillsPage()
        self.code_page = CodePage()
        self.stats_page = StatsPage()
        self.settings_page = SettingsPage()
        
        self.stack.addWidget(self.chat_page)
        self.stack.addWidget(self.files_page)
        self.stack.addWidget(self.tasks_page)
        self.stack.addWidget(self.browser_page)
        self.stack.addWidget(self.skills_page)
        self.stack.addWidget(self.code_page)
        self.stack.addWidget(self.stats_page)
        self.stack.addWidget(self.settings_page)
        
        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)
        root.addWidget(self.stack, stretch=1)

        self.setStyleSheet("""
            QMainWindow { background: #0d1117; }
            QWidget { background: #0d1117; color: #e6edf3; }
            QLabel { background: transparent; }
            QScrollBar:vertical { background: #0d1117; width: 8px; border: none; }
            QScrollBar::handle:vertical { background: #30363d; border-radius: 4px; min-height: 20px; }
            QScrollBar::handle:vertical:hover { background: #484f58; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
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
