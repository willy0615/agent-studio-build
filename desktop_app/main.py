#!/usr/bin/env python3
"""
Agent Studio V5 - 真实工具集成版
所有功能通过 Gateway /v1/chat/completions 调用 Agent 执行工具
"""

import sys
import os
import json
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
    QDoubleSpinBox, QProgressBar, QTabWidget, QPlainTextEdit, QTextBrowser,
    QInputDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer, QMutex
from PyQt6.QtGui import QColor, QPixmap, QImage, QFont, QIcon

import requests


# ============================================================
# Gateway API
# ============================================================
class GatewayAPI:
    """通过 Gateway /v1/chat/completions 让 Agent 执行工具"""

    def __init__(self):
        self.base_url = ""
        self.token = ""
        self.model = "qclaw/modelroute"
        self._load_config()

    def _load_config(self):
        config_path = Path.home() / ".qclaw" / "openclaw.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                port = data.get("gateway", {}).get("port", 52402)
                self.base_url = "http://127.0.0.1:%d" % port
                self.token = data.get("gateway", {}).get("auth", {}).get("token", "")

    def _headers(self):
        return {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self.token
        }

    def chat_stream(self, messages, model=None, on_chunk=None):
        """流式对话，每收到一段文字回调 on_chunk"""
        url = self.base_url + "/v1/chat/completions"
        payload = {
            "model": model or self.model,
            "messages": messages,
            "stream": True,
            "temperature": 0.3,
            "max_tokens": 4096
        }
        full = ""
        try:
            with requests.post(url, headers=self._headers(), json=payload, stream=True, timeout=120) as resp:
                if resp.status_code != 200:
                    return "HTTP Error %d: %s" % (resp.status_code, resp.text[:200])
                for line in resp.iter_lines():
                    if line:
                        line = line.decode("utf-8")
                        if line.startswith("data: "):
                            d = line[6:]
                            if d == "[DONE]":
                                break
                            try:
                                chunk = json.loads(d)
                                c = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if c:
                                    full += c
                                    if on_chunk:
                                        on_chunk(c)
                            except:
                                pass
            return full
        except requests.Timeout:
            return "Error: request timeout"
        except Exception as e:
            return "Error: %s" % str(e)

    def call_tool_via_agent(self, instruction, model=None):
        """通过 Agent 执行工具调用"""
        messages = [
            {"role": "system", "content": "You are a tool executor. Execute the requested tool call and return ONLY the raw result data. Do not add explanations."},
            {"role": "user", "content": instruction}
        ]
        return self.chat_stream(messages, model=model)

    def list_models(self):
        """从配置获取可用模型"""
        models = []
        config_path = Path.home() / ".qclaw" / "openclaw.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                providers = data.get("models", {}).get("providers", {})
                for prov_name, prov in providers.items():
                    for m in prov.get("models", []):
                        models.append({
                            "id": "%s/%s" % (prov_name, m["id"]),
                            "name": m.get("name", m["id"]),
                            "provider": prov_name
                        })
        return models


API = GatewayAPI()


# ============================================================
# Worker Thread
# ============================================================
class ToolWorker(QThread):
    """后台线程执行 Agent 工具调用"""
    result_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, instruction, model=None):
        super().__init__()
        self.instruction = instruction
        self.model = model

    def run(self):
        try:
            result = API.call_tool_via_agent(self.instruction, self.model)
            self.result_ready.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))


def _safe_html(text):
    """转义 HTML 特殊字符"""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ============================================================
# 聊天页面
# ============================================================
class ChatPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.messages = []
        self.worker = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("模型:"))
        self.model_combo = QComboBox()
        for m in API.list_models():
            self.model_combo.addItem("%s (%s)" % (m["name"], m["provider"]), m["id"])
        toolbar.addWidget(self.model_combo, stretch=1)
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self.clear_chat)
        toolbar.addWidget(clear_btn)
        layout.addLayout(toolbar)

        self.msg_area = QTextEdit()
        self.msg_area.setReadOnly(True)
        self.msg_area.setFont(QFont("Consolas", 11))
        layout.addWidget(self.msg_area, stretch=1)

        input_row = QHBoxLayout()
        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("输入消息...")
        self.input_field.setMaximumHeight(80)
        input_row.addWidget(self.input_field, stretch=1)
        send_btn = QPushButton("发送")
        send_btn.setFixedWidth(80)
        send_btn.clicked.connect(self.send_message)
        input_row.addWidget(send_btn)
        layout.addLayout(input_row)

    def clear_chat(self):
        self.messages.clear()
        self.msg_area.clear()

    def send_message(self):
        text = self.input_field.toPlainText().strip()
        if not text:
            return
        self.msg_area.append('<div style="color:#58a6ff;margin:4px 0"><b>你:</b> %s</div>' % _safe_html(text))
        self.input_field.clear()
        self.messages.append({"role": "user", "content": text})
        model_id = self.model_combo.currentData()

        self.msg_area.append('<div style="color:#8b949e;margin:4px 0"><b>AI:</b> </div>')
        cursor = self.msg_area.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)

        full = ""
        def on_chunk(c):
            nonlocal full
            full += c
            cursor.insertText(c)
            self.msg_area.setTextCursor(cursor)
            QApplication.processEvents()

        def do_chat():
            result = API.chat_stream(self.messages, model=model_id, on_chunk=on_chunk)
            if result and result == full:
                self.messages.append({"role": "assistant", "content": full})
            self.msg_area.append("")

        threading.Thread(target=do_chat, daemon=True).start()


# ============================================================
# 会话管理
# ============================================================
class SessionsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(15000)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("会话管理"))

        toolbar = QHBoxLayout()
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(refresh_btn)
        self.detail_area = QTextEdit()
        self.detail_area.setReadOnly(True)
        self.detail_area.setFont(QFont("Consolas", 10))
        toolbar.addWidget(self.detail_area, stretch=1)
        send_btn = QPushButton("发消息到选中会话")
        send_btn.clicked.connect(self.send_to_session)
        toolbar.addWidget(send_btn)
        layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Key", "状态", "模型", "Tokens", "活跃"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.cellDoubleClicked.connect(self.show_history)
        layout.addWidget(self.table, stretch=1)

        self.status = QLabel("就绪")
        self.status.setStyleSheet("color:#8b949e;")
        layout.addWidget(self.status)
        self.refresh()

    def refresh(self):
        self.status.setText("获取中...")
        self.status.setStyleSheet("color:#d29922;")
        w = ToolWorker("Call sessions_list with limit=50. Return ONLY a JSON array of objects with: sessionKey, status, model, contextTokens, lastActive.")
        w.result_ready.connect(self._loaded)
        w.error_occurred.connect(lambda e: self.status.setText("错误: " + str(e)[:80]))
        w.start()

    def _loaded(self, result):
        self.status.setText("已加载 " + datetime.now().strftime("%H:%M:%S"))
        self.status.setStyleSheet("color:#8b949e;")
        try:
            text = result.strip()
            if text.startswith("```"): text = text.split("\n", 1)[1]
            if text.endswith("```"): text = text[:-3]
            sessions = json.loads(text.strip())
            if not isinstance(sessions, list): sessions = [sessions]
            self.table.setRowCount(len(sessions))
            for i, s in enumerate(sessions):
                if isinstance(s, dict):
                    self.table.setItem(i, 0, QTableWidgetItem(str(s.get("sessionKey", ""))))
                    self.table.setItem(i, 1, QTableWidgetItem(str(s.get("status", ""))))
                    self.table.setItem(i, 2, QTableWidgetItem(str(s.get("model", ""))))
                    self.table.setItem(i, 3, QTableWidgetItem(str(s.get("contextTokens", ""))))
                    self.table.setItem(i, 4, QTableWidgetItem(str(s.get("lastActive", ""))))
        except Exception:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("解析失败"))
            self.detail_area.setPlainText(result[:2000])

    def show_history(self, row, col):
        item = self.table.item(row, 0)
        if not item: return
        key = item.text()
        self.status.setText("获取历史...")
        w = ToolWorker("Call sessions_history with sessionKey='%s', limit=20. Return ONLY JSON array." % key)
        w.result_ready.connect(lambda r: self.detail_area.setPlainText(r[:3000]))
        w.error_occurred.connect(lambda e: self.status.setText("错误"))
        w.start()

    def send_to_session(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请选择会话")
            return
        key = self.table.item(row, 0).text() if self.table.item(row, 0) else ""
        msg, ok = QInputDialog.getText(self, "发送消息", "消息:")
        if ok and msg:
            w = ToolWorker("Call sessions_send with sessionKey='%s', message='%s'. Return result." % (key, msg))
            w.result_ready.connect(lambda r: self.detail_area.setPlainText("结果: " + r[:2000]))
            w.start()


# ============================================================
# 浏览器控制
# ============================================================
class BrowserPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.history = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("浏览器控制"))

        ctrl = QHBoxLayout()
        for label, cmd in [
            ("状态", "Call browser with action='status'. Return raw JSON."),
            ("启动", "Call browser with action='start'. Return raw JSON."),
            ("截图", "Call browser with action='screenshot'. Return raw JSON."),
            ("停止", "Call browser with action='stop'. Return raw JSON."),
        ]:
            b = QPushButton(label)
            b.clicked.connect(lambda _, c=cmd: self._exec(c))
            ctrl.addWidget(b)
        open_btn = QPushButton("打开网页")
        open_btn.clicked.connect(self._open_url)
        ctrl.addWidget(open_btn)
        layout.addLayout(ctrl)

        url_row = QHBoxLayout()
        url_row.addWidget(QLabel("URL:"))
        self.url_input = QLineEdit("https://google.com")
        url_row.addWidget(self.url_input, stretch=1)
        layout.addLayout(url_row)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        self.result_area.setFont(QFont("Consolas", 10))
        splitter.addWidget(self.result_area)

        self.history_list = QListWidget()
        self.history_list.setFont(QFont("Consolas", 9))
        self.history_list.setMaximumHeight(100)
        splitter.addWidget(self.history_list)
        layout.addWidget(splitter, stretch=1)

    def _open_url(self):
        url = self.url_input.text().strip()
        if url:
            self._exec("Call browser with action='open', url='%s'. Return raw JSON." % url)

    def _exec(self, instruction):
        ts = datetime.now().strftime("%H:%M:%S")
        self.result_area.append('<span style="color:#8b949e">[%s] 执行中...</span>' % ts)
        self.history.append("[%s] %s" % (ts, instruction[:60]))
        self.history_list.clear()
        for h in self.history[-10:]:
            self.history_list.addItem(h)
        w = ToolWorker(instruction)
        w.result_ready.connect(lambda r: self.result_area.append('<span style="color:#3fb950">%s</span>' % _safe_html(r)))
        w.error_occurred.connect(lambda e: self.result_area.append('<span style="color:#f85149">%s</span>' % _safe_html(str(e))))
        w.start()


# ============================================================
# 节点管理
# ============================================================
class NodesPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("节点管理"))

        ctrl = QHBoxLayout()
        for label, cmd in [
            ("节点状态", "Call nodes with action='status'. Return raw JSON."),
            ("设备信息", "Call nodes with action='device_info'. Return raw JSON."),
            ("远程拍照", "Call nodes with action='camera_snap', facing='back'. Return raw JSON."),
            ("获取位置", "Call nodes with action='location_get'. Return raw JSON."),
        ]:
            b = QPushButton(label)
            b.clicked.connect(lambda _, c=cmd: self._exec(c))
            ctrl.addWidget(b)
        layout.addLayout(ctrl)

        self.node_input = QLineEdit()
        self.node_input.setPlaceholderText("节点 ID（可选）")
        layout.addWidget(self.node_input)

        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        self.result_area.setFont(QFont("Consolas", 10))
        layout.addWidget(self.result_area, stretch=1)

    def _exec(self, instruction):
        nid = self.node_input.text().strip()
        if nid:
            instruction = instruction.replace("'. Return", "', node='%s'. Return" % nid)
        self.result_area.clear()
        self.result_area.append('<span style="color:#8b949e">执行中...</span>')
        w = ToolWorker(instruction)
        w.result_ready.connect(lambda r: self.result_area.setPlainText(r))
        w.error_occurred.connect(lambda e: self.result_area.append('<span style="color:#f85149">Error: %s</span>' % str(e)))
        w.start()


# ============================================================
# 消息推送
# ============================================================
class MessagePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("消息推送"))

        form = QFormLayout()
        self.channel_combo = QComboBox()
        self.channel_combo.addItems(["telegram", "discord", "slack", "wechat", "signal", "whatsapp"])
        form.addRow("渠道:", self.channel_combo)
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("目标用户ID")
        form.addRow("目标:", self.target_input)
        self.msg_input = QTextEdit()
        self.msg_input.setMaximumHeight(80)
        self.msg_input.setPlaceholderText("消息内容")
        form.addRow("消息:", self.msg_input)
        layout.addLayout(form)

        send_btn = QPushButton("发送")
        send_btn.clicked.connect(self.send)
        layout.addWidget(send_btn)

        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        self.result_area.setFont(QFont("Consolas", 10))
        layout.addWidget(self.result_area, stretch=1)

    def send(self):
        ch = self.channel_combo.currentText()
        target = self.target_input.text().strip()
        msg = self.msg_input.toPlainText().strip()
        if not target or not msg:
            QMessageBox.warning(self, "提示", "填写目标和消息")
            return
        self.result_area.append('<span style="color:#8b949e">发送中...</span>')
        w = ToolWorker("Call message with action='send', channel='%s', target='%s', message='%s'. Return raw JSON." % (ch, target, msg))
        w.result_ready.connect(lambda r: self.result_area.append('<span style="color:#3fb950">%s</span>' % _safe_html(r)))
        w.error_occurred.connect(lambda e: self.result_area.append('<span style="color:#f85149">%s</span>' % _safe_html(str(e))))
        w.start()


# ============================================================
# 任务调度
# ============================================================
class TasksPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(30000)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("任务调度"))

        toolbar = QHBoxLayout()
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(refresh_btn)
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self.add_task)
        toolbar.addWidget(add_btn)
        layout.addLayout(toolbar)

        form = QFrame()
        fl = QFormLayout(form)
        self.cron_input = QLineEdit("0 9 * * *")
        self.cron_input.setPlaceholderText("Cron 表达式")
        fl.addRow("Cron:", self.cron_input)
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("任务消息")
        fl.addRow("消息:", self.task_input)
        layout.addWidget(form)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Job ID", "名称", "Cron", "状态", "创建时间", "操作"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table, stretch=1)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(80)
        self.log.setFont(QFont("Consolas", 9))
        layout.addWidget(self.log)
        self.refresh()

    def refresh(self):
        self.log.append('<span style="color:#8b949e">[%s] 刷新...</span>' % datetime.now().strftime("%H:%M:%S"))
        w = ToolWorker("Call cron with action='list', includeDisabled=True. Return ONLY a JSON array of jobs with: jobId, name, enabled, schedule(expr), createdAt.")
        w.result_ready.connect(self._loaded)
        w.error_occurred.connect(lambda e: self.log.append('<span style="color:#f85149">%s</span>' % _safe_html(str(e))))
        w.start()

    def _loaded(self, result):
        try:
            text = result.strip()
            if text.startswith("```"): text = text.split("\n", 1)[1]
            if text.endswith("```"): text = text[:-3]
            jobs = json.loads(text.strip())
            if not isinstance(jobs, list): jobs = [jobs]
            self.table.setRowCount(len(jobs))
            for i, j in enumerate(jobs):
                if isinstance(j, dict):
                    jid = str(j.get("jobId", ""))
                    name = str(j.get("name", ""))
                    sched = j.get("schedule", {})
                    expr = sched.get("expr", "") if isinstance(sched, dict) else str(sched)
                    en = str(j.get("enabled", ""))
                    self.table.setItem(i, 0, QTableWidgetItem(jid))
                    self.table.setItem(i, 1, QTableWidgetItem(name))
                    self.table.setItem(i, 2, QTableWidgetItem(expr))
                    self.table.setItem(i, 3, QTableWidgetItem(en))
                    self.table.setItem(i, 4, QTableWidgetItem(str(j.get("createdAt", ""))))
                    btn = QPushButton("启用" if en == "False" else "禁用")
                    btn.clicked.connect(lambda _, jid=jid, en=en: self.toggle(jid, en))
                    self.table.setCellWidget(i, 5, btn)
            self.log.append('<span style="color:#3fb950">已加载 %d 个任务</span>' % len(jobs))
        except Exception:
            self.log.append('<span style="color:#d29922">解析失败</span>')

    def add_task(self):
        ce = self.cron_input.text().strip()
        msg = self.task_input.text().strip()
        if not ce or not msg:
            QMessageBox.warning(self, "提示", "填写 Cron 和消息")
            return
        w = ToolWorker("Call cron with action='add', schedule kind='cron' expr='%s', payload kind='systemEvent' text='%s', sessionTarget='main', enabled=True. Return raw JSON." % (ce, msg))
        w.result_ready.connect(lambda r: (self.log.append('<span style="color:#3fb950">%s</span>' % _safe_html(r[:200])), self.refresh()))
        w.error_occurred.connect(lambda e: self.log.append('<span style="color:#f85149">%s</span>' % _safe_html(str(e))))
        w.start()

    def toggle(self, jid, cur):
        new = cur != "True"
        w = ToolWorker("Call cron with action='update', jobId='%s', patch enabled=%s. Return JSON." % (jid, str(new).lower()))
        w.result_ready.connect(lambda r: (self.log.append('<span style="color:#3fb950">%s</span>' % _safe_html(r[:200])), self.refresh()))
        w.start()


# ============================================================
# 技能管理
# ============================================================
class SkillsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("技能管理"))

        ctrl = QHBoxLayout()
        list_btn = QPushButton("列出 Agent")
        list_btn.clicked.connect(self.list_agents)
        ctrl.addWidget(list_btn)
        install_btn = QPushButton("安装技能")
        install_btn.clicked.connect(self.install_skill)
        ctrl.addWidget(install_btn)
        layout.addLayout(ctrl)

        self.skill_input = QLineEdit()
        self.skill_input.setPlaceholderText("技能名称")
        layout.addWidget(self.skill_input)

        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        self.result_area.setFont(QFont("Consolas", 10))
        layout.addWidget(self.result_area, stretch=1)

    def list_agents(self):
        self.result_area.append('<span style="color:#8b949e">获取中...</span>')
        w = ToolWorker("Call agents_list. Return raw JSON.")
        w.result_ready.connect(lambda r: self.result_area.append(_safe_html(r)))
        w.error_occurred.connect(lambda e: self.result_area.append('<span style="color:#f85149">%s</span>' % _safe_html(str(e))))
        w.start()

    def install_skill(self):
        name = self.skill_input.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "输入技能名称")
            return
        self.result_area.append('<span style="color:#8b949e">安装 %s...</span>' % name)
        w = ToolWorker("Call skillhub_install with action='install_skill', skillName='%s'. Return raw result." % name)
        w.result_ready.connect(lambda r: self.result_area.append(_safe_html(r)))
        w.error_occurred.connect(lambda e: self.result_area.append('<span style="color:#f85149">%s</span>' % _safe_html(str(e))))
        w.start()


# ============================================================
# 记忆管理
# ============================================================
class MemoryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("记忆管理"))

        row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索关键词...")
        row.addWidget(self.search_input, stretch=1)
        mem_btn = QPushButton("记忆搜索")
        mem_btn.clicked.connect(self.mem_search)
        row.addWidget(mem_btn)
        lcm_btn = QPushButton("LCM 搜索")
        lcm_btn.clicked.connect(self.lcm_search)
        row.addWidget(lcm_btn)
        layout.addLayout(row)

        local_row = QHBoxLayout()
        local_row.addWidget(QLabel("本地:"))
        mem_file = QPushButton("MEMORY.md")
        mem_file.clicked.connect(lambda: self._show(Path.home() / ".qclaw" / "workspace-ua58rsb93veqtxl7" / "MEMORY.md"))
        local_row.addWidget(mem_file)
        today = datetime.now().strftime("%Y-%m-%d")
        td_btn = QPushButton(today + ".md")
        td_btn.clicked.connect(lambda: self._show(Path.home() / ".qclaw" / "workspace-ua58rsb93veqtxl7" / "memory" / (today + ".md")))
        local_row.addWidget(td_btn)
        local_row.addStretch()
        layout.addLayout(local_row)

        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        self.result_area.setFont(QFont("Consolas", 10))
        layout.addWidget(self.result_area, stretch=1)

    def _show(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.result_area.setPlainText(f.read()[:5000])
        except Exception as e:
            self.result_area.setPlainText("Error: " + str(e))

    def mem_search(self):
        q = self.search_input.text().strip()
        if not q: return
        self.result_area.append('<span style="color:#8b949e">搜索: %s...</span>' % q)
        w = ToolWorker("Call memory_search with query='%s'. Return raw JSON." % q)
        w.result_ready.connect(lambda r: self.result_area.append(_safe_html(r)))
        w.error_occurred.connect(lambda e: self.result_area.append('<span style="color:#f85149">%s</span>' % _safe_html(str(e))))
        w.start()

    def lcm_search(self):
        q = self.search_input.text().strip()
        if not q: return
        self.result_area.append('<span style="color:#8b949e">LCM: %s...</span>' % q)
        w = ToolWorker("Call lcm_grep with pattern='%s', mode='full_text', limit=20. Return raw JSON." % q)
        w.result_ready.connect(lambda r: self.result_area.append(_safe_html(r)))
        w.error_occurred.connect(lambda e: self.result_area.append('<span style="color:#f85149">%s</span>' % _safe_html(str(e))))
        w.start()


# ============================================================
# 文件管理
# ============================================================
class FilesPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        row.addWidget(QLabel("路径:"))
        self.path_input = QLineEdit(str(Path.home()))
        row.addWidget(self.path_input, stretch=1)
        b = QPushButton("浏览")
        b.clicked.connect(self.browse)
        row.addWidget(b)
        layout.addLayout(row)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["名称", "大小", "修改时间"])
        self.tree.doubleClicked.connect(self.preview_file)
        layout.addWidget(self.tree, stretch=1)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMaximumHeight(200)
        self.preview.setFont(QFont("Consolas", 9))
        layout.addWidget(self.preview)

        b2 = QPushButton("刷新")
        b2.clicked.connect(self.load)
        layout.addWidget(b2)
        self.load()

    def browse(self):
        d = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if d:
            self.path_input.setText(d)
            self.load()

    def load(self):
        self.tree.clear()
        p = Path(self.path_input.text())
        if not p.exists(): return
        for item in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name)):
            sz = self._fmt(item.stat().st_size) if item.is_file() else "<DIR>"
            mt = datetime.fromtimestamp(item.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            self.tree.addTopLevelItem(QTreeWidgetItem([item.name, sz, mt]))

    def preview_file(self, idx):
        if idx.column() != 0: return
        p = Path(self.path_input.text()) / idx.data()
        if p.is_file():
            try:
                self.preview.setPlainText(open(p, "r", encoding="utf-8", errors="replace").read()[:3000])
            except:
                self.preview.setPlainText("(二进制文件)")

    def _fmt(self, sz):
        for u in ["B", "KB", "MB", "GB"]:
            if sz < 1024: return "%d %s" % (sz, u)
            sz //= 1024
        return "%d TB" % sz


# ============================================================
# 命令执行
# ============================================================
class ExecPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        row.addWidget(QLabel("命令:"))
        self.cmd = QLineEdit()
        self.cmd.setPlaceholderText("echo hello")
        row.addWidget(self.cmd, stretch=1)
        b = QPushButton("执行")
        b.clicked.connect(self.run)
        row.addWidget(b)
        layout.addLayout(row)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Consolas", 10))
        layout.addWidget(self.output, stretch=1)

    def run(self):
        c = self.cmd.text().strip()
        if not c: return
        self.output.append('<span style="color:#8b949e">[%s] $ %s</span>' % (datetime.now().strftime("%H:%M:%S"), _safe_html(c)))
        try:
            r = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace")
            if r.stdout: self.output.append(_safe_html(r.stdout))
            if r.stderr: self.output.append('<span style="color:#f85149">%s</span>' % _safe_html(r.stderr))
        except subprocess.TimeoutExpired:
            self.output.append('<span style="color:#f85149">超时</span>')
        except Exception as e:
            self.output.append('<span style="color:#f85149">%s</span>' % _safe_html(str(e)))


# ============================================================
# 主窗口
# ============================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Agent Studio V5")
        self.setMinimumSize(1400, 900)
        self.init_ui()
        self.apply_theme()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        ml = QHBoxLayout(central)
        ml.setContentsMargins(0, 0, 0, 0)

        sidebar = QFrame()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("background: #161b22;")
        sl = QVBoxLayout(sidebar)

        logo = QLabel("Agent Studio")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet("color: #e6edf3; font-size: 18px; font-weight: bold; padding: 20px;")
        sl.addWidget(logo)

        self.pages = QStackedWidget()
        nav = [
            ("对话", ChatPage()),
            ("会话", SessionsPage()),
            ("浏览器", BrowserPage()),
            ("技能", SkillsPage()),
            ("任务", TasksPage()),
            ("节点", NodesPage()),
            ("消息", MessagePage()),
            ("记忆", MemoryPage()),
            ("文件", FilesPage()),
            ("命令", ExecPage()),
        ]

        self.nav_btns = []
        for i, (name, page) in enumerate(nav):
            btn = QPushButton(name)
            btn.setStyleSheet("""
                QPushButton { background: transparent; color: #c9d1d9; border: none; text-align: left; padding: 12px 20px; }
                QPushButton:hover { background: #21262d; }
                QPushButton:checked { background: #21262d; color: #e6edf3; }
            """)
            btn.setCheckable(True)
            btn.setChecked(i == 0)
            btn.clicked.connect(lambda _, idx=i: self._switch(idx))
            sl.addWidget(btn)
            self.nav_btns.append(btn)
            self.pages.addWidget(page)

        sl.addStretch()
        ml.addWidget(sidebar)
        ml.addWidget(self.pages, stretch=1)

    def _switch(self, idx):
        for i, b in enumerate(self.nav_btns):
            b.setChecked(i == idx)
        self.pages.setCurrentIndex(idx)

    def apply_theme(self):
        self.setStyleSheet("""
            QMainWindow { background: #0d1117; }
            QWidget { background: transparent; }
            QLabel { background: transparent; color: #e6edf3; }
            QTextEdit { background: #161b22; color: #e6edf3; border: 1px solid #30363d; }
            QLineEdit { background: #161b22; color: #e6edf3; border: 1px solid #30363d; padding: 4px; }
            QPushButton { background: #21262d; color: #e6edf3; border: 1px solid #30363d; padding: 6px 12px; }
            QPushButton:hover { background: #30363d; }
            QComboBox { background: #161b22; color: #e6edf3; border: 1px solid #30363d; padding: 4px; }
            QTableWidget { background: #161b22; color: #e6edf3; border: 1px solid #30363d; gridline-color: #30363d; }
            QHeaderView::section { background: #21262d; color: #e6edf3; border: 1px solid #30363d; padding: 4px; }
            QTreeWidget { background: #161b22; color: #e6edf3; border: 1px solid #30363d; }
            QListWidget { background: #161b22; color: #e6edf3; border: 1px solid #30363d; }
            QSplitter::handle { background: #30363d; }
        """)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = MainWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
