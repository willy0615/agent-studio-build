#!/usr/bin/env python3
"""
Agent Studio V5 - Full Feature Edition
All features via Gateway /v1/chat/completions + Multi-Agent Collaboration
"""

import sys
import os
import json
import subprocess
import threading
import base64
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
    QInputDialog, QSizePolicy, QToolBar, QStatusBar, QMenu, QMenuBar,
    QAbstractItemView, QTextCursor, QCompleter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer, QMutex, QBuffer, QByteArray
from PyQt6.QtGui import QColor, QPixmap, QImage, QFont, QIcon, QAction

import requests


# ============================================================
# Gateway API - Core
# ============================================================
class GatewayAPI:
    def __init__(self):
        self.base_url = ""
        self.token = ""
        self.model = "qclaw/modelroute"
        self._load_config()

    def _load_config(self):
        p = Path.home() / ".qclaw" / "openclaw.json"
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    port = data.get("gateway", {}).get("port", 52402)
                    self.base_url = "http://127.0.0.1:%d" % port
                    self.token = data.get("gateway", {}).get("auth", {}).get("token", "")
            except Exception:
                pass

    def _headers(self):
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = "Bearer " + self.token
        return h

    def chat_stream(self, messages, model=None, on_chunk=None):
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
                    return "HTTP Error %d: %s" % (resp.status_code, resp.text[:500])
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
                            except Exception:
                                pass
            return full
        except requests.Timeout:
            return "Error: request timeout (120s)"
        except requests.ConnectionError:
            return "Error: cannot connect to Gateway at %s" % self.base_url
        except Exception as e:
            return "Error: %s" % str(e)

    def call_tool_via_agent(self, instruction, model=None):
        messages = [
            {"role": "system", "content": "You are a tool executor. Execute the requested tool call and return ONLY the raw result data. Do not add explanations. Do not wrap in markdown code blocks."},
            {"role": "user", "content": instruction}
        ]
        return self.chat_stream(messages, model=model)

    def list_models(self):
        models = []
        p = Path.home() / ".qclaw" / "openclaw.json"
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    providers = data.get("models", {}).get("providers", {})
                    for prov_name, prov in providers.items():
                        for m in prov.get("models", []):
                            models.append({
                                "id": "%s/%s" % (prov_name, m["id"]),
                                "name": m.get("name", m["id"]),
                                "provider": prov_name
                            })
            except Exception:
                pass
        return models


API = GatewayAPI()


# ============================================================
# Worker Threads
# ============================================================
class ToolWorker(QThread):
    result_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    progress_text = pyqtSignal(str)

    def __init__(self, instruction, model=None):
        super().__init__()
        self.instruction = instruction
        self.model = model

    def run(self):
        try:
            self.progress_text.emit("executing")
            result = API.call_tool_via_agent(self.instruction, self.model)
            self.result_ready.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))


def _safe_html(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _unwrap_json(text):
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1]
    if t.endswith("```"):
        t = t[:-3]
    if t.startswith("json"):
        t = t[4:].strip()
    return t.strip()


# ============================================================
# ChatPage - Streaming conversation
# ============================================================
class ChatPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.messages = []
        self.lock = QMutex()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        for m in API.list_models():
            self.model_combo.addItem("%s (%s)" % (m["name"], m["provider"]), m["id"])
        toolbar.addWidget(self.model_combo, stretch=1)
        self.thinking_cb = QCheckBox("Thinking")
        toolbar.addWidget(self.thinking_cb)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_chat)
        toolbar.addWidget(clear_btn)
        layout.addLayout(toolbar)

        self.msg_area = QTextEdit()
        self.msg_area.setReadOnly(True)
        self.msg_area.setFont(QFont("Consolas", 11))
        layout.addWidget(self.msg_area, stretch=1)

        input_row = QHBoxLayout()
        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("Type message...")
        self.input_field.setMaximumHeight(80)
        input_row.addWidget(self.input_field, stretch=1)
        send_btn = QPushButton("Send")
        send_btn.setFixedWidth(80)
        send_btn.clicked.connect(self.send_message)
        input_row.addWidget(send_btn)
        layout.addLayout(input_row)

    def clear_chat(self):
        self.lock.lock()
        self.messages.clear()
        self.lock.unlock()
        self.msg_area.clear()

    def send_message(self):
        text = self.input_field.toPlainText().strip()
        if not text:
            return
        self.msg_area.append('<div style="color:#58a6ff;margin:4px 0"><b>You:</b> %s</div>' % _safe_html(text))
        self.input_field.clear()
        self.lock.lock()
        self.messages.append({"role": "user", "content": text})
        self.lock.unlock()
        model_id = self.model_combo.currentData()

        self.msg_area.append('<div style="color:#8b949e;margin:4px 0"><b>AI:</b> </div>')
        cursor = self.msg_area.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)

        full = [""]
        def on_chunk(c):
            full[0] += c
            cursor.insertText(c)
            self.msg_area.setTextCursor(cursor)
            QApplication.processEvents()

        def do_chat():
            result = API.chat_stream(self.messages, model=model_id, on_chunk=on_chunk)
            if result and result == full[0]:
                self.lock.lock()
                self.messages.append({"role": "assistant", "content": full[0]})
                self.lock.unlock()
            self.msg_area.append("")

        threading.Thread(target=do_chat, daemon=True).start()


# ============================================================
# SessionsPage - Full session management
# ============================================================
class SessionsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.sessions_data = []
        self.init_ui()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(15000)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Session Management"))

        toolbar = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(refresh_btn)
        send_btn = QPushButton("Send to Selected")
        send_btn.clicked.connect(self.send_to_session)
        toolbar.addWidget(send_btn)
        spawn_btn = QPushButton("Spawn SubAgent")
        spawn_btn.clicked.connect(self.spawn_subagent)
        toolbar.addWidget(spawn_btn)
        layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Key", "Status", "Model", "Tokens", "Active"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.cellDoubleClicked.connect(self.show_history)
        layout.addWidget(self.table, stretch=1)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self.detail_area = QTextEdit()
        self.detail_area.setReadOnly(True)
        self.detail_area.setFont(QFont("Consolas", 10))
        splitter.addWidget(self.detail_area)

        spawn_form = QFrame()
        fl = QFormLayout(spawn_form)
        self.spawn_task = QLineEdit()
        self.spawn_task.setPlaceholderText("Task description for new Agent...")
        fl.addRow("Spawn Task:", self.spawn_task)
        splitter.addWidget(spawn_form)
        layout.addWidget(splitter, stretch=1)

        self.status = QLabel("Ready")
        self.status.setStyleSheet("color:#8b949e;")
        layout.addWidget(self.status)
        self.refresh()

    def refresh(self):
        self.status.setText("Loading...")
        self.status.setStyleSheet("color:#d29922;")
        w = ToolWorker("Call sessions_list with limit=50. Return ONLY a JSON array with sessionKey, status, model, contextTokens, lastActive.")
        w.result_ready.connect(self._loaded)
        w.error_occurred.connect(lambda e: self.status.setText("Error: " + str(e)[:80]))
        w.start()

    def _loaded(self, result):
        self.status.setText("Loaded " + datetime.now().strftime("%H:%M:%S"))
        self.status.setStyleSheet("color:#8b949e;")
        try:
            sessions = json.loads(_unwrap_json(result))
            if not isinstance(sessions, list):
                sessions = [sessions]
            self.sessions_data = [s for s in sessions if isinstance(s, dict)]
            self.table.setRowCount(len(self.sessions_data))
            for i, s in enumerate(self.sessions_data):
                self.table.setItem(i, 0, QTableWidgetItem(str(s.get("sessionKey", ""))))
                self.table.setItem(i, 1, QTableWidgetItem(str(s.get("status", ""))))
                self.table.setItem(i, 2, QTableWidgetItem(str(s.get("model", ""))))
                self.table.setItem(i, 3, QTableWidgetItem(str(s.get("contextTokens", ""))))
                self.table.setItem(i, 4, QTableWidgetItem(str(s.get("lastActive", ""))))
        except Exception:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("Parse error"))
            self.detail_area.setPlainText(result[:2000])

    def show_history(self, row, col):
        item = self.table.item(row, 0)
        if not item:
            return
        key = item.text()
        self.status.setText("Fetching history...")
        w = ToolWorker("Call sessions_history with sessionKey='%s', limit=30, includeTools=true. Return ONLY JSON array." % key)
        w.result_ready.connect(lambda r: self.detail_area.setPlainText(r[:5000]))
        w.error_occurred.connect(lambda e: self.status.setText("Error"))
        w.start()

    def send_to_session(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "Select a session first")
            return
        key = self.table.item(row, 0).text() if self.table.item(row, 0) else ""
        msg, ok = QInputDialog.getText(self, "Send Message", "Message:")
        if ok and msg:
            w = ToolWorker("Call sessions_send with sessionKey='%s', message='%s'. Return raw result." % (key, msg))
            w.result_ready.connect(lambda r: self.detail_area.setPlainText("Result: " + r[:2000]))
            w.start()

    def spawn_subagent(self):
        task = self.spawn_task.text().strip()
        if not task:
            QMessageBox.warning(self, "Warning", "Enter a task for the sub-agent")
            return
        self.status.setText("Spawning sub-agent...")
        w = ToolWorker("Call sessions_spawn with task='%s', mode='run', cleanup='delete'. Return raw result." % task)
        w.result_ready.connect(lambda r: (self.detail_area.setPlainText("Spawn result: " + r[:3000]), self.refresh()))
        w.error_occurred.connect(lambda e: self.status.setText("Spawn failed: " + str(e)[:60]))
        w.start()


# ============================================================
# BrowserPage - Full browser control
# ============================================================
class BrowserPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.history = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Browser Control"))

        # Main controls
        ctrl = QHBoxLayout()
        actions = [
            ("Status", "Call browser with action='status'. Return raw JSON."),
            ("Start", "Call browser with action='start'. Return raw JSON."),
            ("Stop", "Call browser with action='stop'. Return raw JSON."),
            ("Tabs", "Call browser with action='tabs'. Return raw JSON."),
            ("Profiles", "Call browser with action='profiles'. Return raw JSON."),
        ]
        for label, cmd in actions:
            b = QPushButton(label)
            b.clicked.connect(lambda _, c=cmd: self._exec(c))
            ctrl.addWidget(b)
        layout.addLayout(ctrl)

        # URL / Screenshot row
        url_row = QHBoxLayout()
        url_row.addWidget(QLabel("URL:"))
        self.url_input = QLineEdit("https://google.com")
        url_row.addWidget(self.url_input, stretch=1)
        open_btn = QPushButton("Open")
        open_btn.clicked.connect(self._open_url)
        url_row.addWidget(open_btn)
        snap_btn = QPushButton("Snapshot(Aria)")
        snap_btn.clicked.connect(lambda: self._exec("Call browser with action='snapshot', snapshotFormat='aria'. Return raw result."))
        url_row.addWidget(snap_btn)
        ss_btn = QPushButton("Screenshot")
        ss_btn.clicked.connect(self._screenshot)
        url_row.addWidget(ss_btn)
        layout.addLayout(url_row)

        # Interaction row
        act_row = QHBoxLayout()
        act_row.addWidget(QLabel("Ref:"))
        self.ref_input = QLineEdit()
        self.ref_input.setPlaceholderText("element ref (e.g. e12)")
        act_row.addWidget(self.ref_input, stretch=1)
        for label, act in [("Click", "click"), ("Type", "type"), ("Hover", "hover"), ("Press", "press")]:
            b = QPushButton(label)
            b.clicked.connect(lambda _, a=act: self._act(a))
            act_row.addWidget(b)
        layout.addLayout(act_row)

        type_row = QHBoxLayout()
        type_row.addWidget(QLabel("Type text:"))
        self.type_input = QLineEdit()
        type_row.addWidget(self.type_input, stretch=1)
        layout.addLayout(type_row)

        # Results
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

    def _screenshot(self):
        self.result_area.append('<span style="color:#8b949e">Taking screenshot...</span>')
        w = ToolWorker("Call browser with action='screenshot', type='png'. Return raw JSON. If it contains a base64 image, return the full base64 data.")
        w.result_ready.connect(self._show_screenshot)
        w.start()

    def _show_screenshot(self, result):
        self.result_area.append('<span style="color:#3fb950">Screenshot received</span>')
        # Check if result contains base64 image data
        try:
            data = _unwrap_json(result)
            # Look for base64 image data
            if "data:image" in data or "base64" in data.lower():
                start = data.find("base64,")
                if start > 0:
                    b64 = data[start + 7:].strip().split('"')[0].split("'")[0].split("}")[0]
                    img_data = base64.b64decode(b64[:500000])
                    img = QImage()
                    img.loadFromData(img_data)
                    pixmap = QPixmap.fromImage(img)
                    cursor = self.result_area.textCursor()
                    cursor.insertImage(pixmap)
                    self.result_area.setTextCursor(cursor)
                else:
                    self.result_area.append(_safe_html(data[:500]))
            else:
                self.result_area.append(_safe_html(data[:500]))
        except Exception:
            self.result_area.append(_safe_html(result[:500]))

    def _act(self, action):
        ref = self.ref_input.text().strip()
        if not ref:
            QMessageBox.warning(self, "Warning", "Enter element ref first (take a snapshot)")
            return
        instruction = "Call browser with action='act', kind='%s', ref='%s'" % (action, ref)
        if action == "type":
            txt = self.type_input.text().strip()
            if txt:
                instruction += ", text='%s'" % txt
        instruction += ". Return raw JSON."
        self._exec(instruction)

    def _exec(self, instruction):
        ts = datetime.now().strftime("%H:%M:%S")
        self.result_area.append('<span style="color:#8b949e">[%s] Executing...</span>' % ts)
        self.history.append("[%s] %s" % (ts, instruction[:80]))
        self.history_list.clear()
        for h in self.history[-10:]:
            self.history_list.addItem(h)
        w = ToolWorker(instruction)
        w.result_ready.connect(lambda r: self.result_area.append('<span style="color:#3fb950">%s</span>' % _safe_html(r)))
        w.error_occurred.connect(lambda e: self.result_area.append('<span style="color:#f85149">%s</span>' % _safe_html(str(e))))
        w.start()


# ============================================================
# NodesPage - Full node management
# ============================================================
class NodesPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Node Management"))

        node_row = QHBoxLayout()
        node_row.addWidget(QLabel("Node ID:"))
        self.node_input = QLineEdit()
        self.node_input.setPlaceholderText("node id (optional)")
        node_row.addWidget(self.node_input, stretch=1)
        layout.addLayout(node_row)

        # Status & Info
        row1 = QHBoxLayout()
        for label, cmd in [
            ("Status", "nodes status"),
            ("Describe", "nodes describe"),
            ("Device Info", "nodes device_info"),
            ("Permissions", "nodes device_permissions"),
            ("Health", "nodes device_health"),
        ]:
            b = QPushButton(label)
            b.clicked.connect(lambda _, c=cmd: self._exec(c))
            row1.addWidget(b)
        layout.addLayout(row1)

        # Camera & Location
        row2 = QHBoxLayout()
        for label, cmd in [
            ("Front Cam", "nodes camera_snap facing='front'"),
            ("Back Cam", "nodes camera_snap facing='back'"),
            ("Location", "nodes location_get"),
            ("Screen Record", "nodes screen_record durationMs='5000'"),
            ("Notifications", "nodes notifications_list"),
        ]:
            b = QPushButton(label)
            b.clicked.connect(lambda _, c=cmd: self._exec(c))
            row2.addWidget(b)
        layout.addLayout(row2)

        # Notify
        notify_row = QHBoxLayout()
        notify_row.addWidget(QLabel("Notify Title:"))
        self.notify_title = QLineEdit()
        notify_row.addWidget(self.notify_title, stretch=1)
        notify_row.addWidget(QLabel("Body:"))
        self.notify_body = QLineEdit()
        notify_row.addWidget(self.notify_body, stretch=1)
        notify_btn = QPushButton("Notify")
        notify_btn.clicked.connect(self.send_notify)
        notify_row.addWidget(notify_btn)
        layout.addLayout(notify_row)

        # Pending
        pend_row = QHBoxLayout()
        pend_btn = QPushButton("Pending Pairings")
        pend_btn.clicked.connect(lambda: self._exec("nodes pending"))
        pend_row.addWidget(pend_btn)
        approve_btn = QPushButton("Approve")
        approve_btn.clicked.connect(self._approve)
        pend_row.addWidget(approve_btn)
        reject_btn = QPushButton("Reject")
        reject_btn.clicked.connect(self._reject)
        pend_row.addWidget(reject_btn)
        layout.addLayout(pend_row)

        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        self.result_area.setFont(QFont("Consolas", 10))
        layout.addWidget(self.result_area, stretch=1)

    def _build_instruction(self, cmd):
        nid = self.node_input.text().strip()
        base = "Call %s" % cmd
        if nid:
            base += ", node='%s'" % nid
        base += ". Return raw JSON."
        return base

    def _exec(self, cmd):
        self.result_area.clear()
        self.result_area.append('<span style="color:#8b949e">Executing...</span>')
        w = ToolWorker(self._build_instruction(cmd))
        w.result_ready.connect(lambda r: self.result_area.setPlainText(r))
        w.error_occurred.connect(lambda e: self.result_area.append('<span style="color:#f85149">Error: %s</span>' % _safe_html(str(e))))
        w.start()

    def send_notify(self):
        title = self.notify_title.text().strip()
        body = self.notify_body.text().strip()
        if not title:
            QMessageBox.warning(self, "Warning", "Enter notify title")
            return
        nid = self.node_input.text().strip()
        cmd = "Call nodes with action='notify', title='%s'" % title
        if body:
            cmd += ", body='%s'" % body
        if nid:
            cmd += ", node='%s'" % nid
        cmd += ". Return raw JSON."
        w = ToolWorker(cmd)
        w.result_ready.connect(lambda r: self.result_area.setPlainText(r))
        w.start()

    def _approve(self):
        rid, ok = QInputDialog.getText(self, "Approve", "Request ID:")
        if ok and rid:
            nid = self.node_input.text().strip()
            cmd = "Call nodes with action='approve', requestId='%s'" % rid
            if nid:
                cmd += ", node='%s'" % nid
            cmd += ". Return raw JSON."
            w = ToolWorker(cmd)
            w.result_ready.connect(lambda r: self.result_area.setPlainText(r))
            w.start()

    def _reject(self):
        rid, ok = QInputDialog.getText(self, "Reject", "Request ID:")
        if ok and rid:
            nid = self.node_input.text().strip()
            cmd = "Call nodes with action='reject', requestId='%s'" % rid
            if nid:
                cmd += ", node='%s'" % nid
            cmd += ". Return raw JSON."
            w = ToolWorker(cmd)
            w.result_ready.connect(lambda r: self.result_area.setPlainText(r))
            w.start()


# ============================================================
# MessagePage - Full messaging
# ============================================================
class MessagePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Message Push"))

        tabs = QTabWidget()

        # Send tab
        send_tab = QWidget()
        sl = QVBoxLayout(send_tab)
        form = QFormLayout()
        self.channel_combo = QComboBox()
        self.channel_combo.addItems(["telegram", "discord", "slack", "wechat", "signal", "whatsapp", "line", "zalo", "irc", "msteams", "nextcloud-talk", "matrix", "bluebubbles", "twitch", "feishu", "googlechat", "synology-chat", "tlon"])
        form.addRow("Channel:", self.channel_combo)
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("Target user/group ID")
        form.addRow("Target:", self.target_input)
        self.msg_input = QTextEdit()
        self.msg_input.setMaximumHeight(100)
        self.msg_input.setPlaceholderText("Message content")
        form.addRow("Message:", self.msg_input)
        self.thread_input = QLineEdit()
        self.thread_input.setPlaceholderText("Thread ID (optional)")
        form.addRow("Thread:", self.thread_input)
        sl.addLayout(form)

        send_row = QHBoxLayout()
        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.send)
        send_row.addWidget(send_btn)
        silent_cb = QCheckBox("Silent")
        send_row.addWidget(silent_cb)
        voice_cb = QCheckBox("As Voice")
        send_row.addWidget(voice_cb)
        sl.addLayout(send_row)
        tabs.addTab(send_tab, "Send")

        # Poll tab
        poll_tab = QWidget()
        pl = QVBoxLayout(poll_tab)
        pf = QFormLayout()
        self.poll_question = QLineEdit()
        self.poll_question.setPlaceholderText("Poll question")
        pf.addRow("Question:", self.poll_question)
        self.poll_options = QLineEdit()
        self.poll_options.setPlaceholderText("Option1, Option2, Option3")
        pf.addRow("Options:", self.poll_options)
        self.poll_hours = QSpinBox()
        self.poll_hours.setRange(1, 168)
        self.poll_hours.setValue(24)
        pf.addRow("Duration(h):", self.poll_hours)
        self.poll_multi_cb = QCheckBox("Multiple choice")
        pf.addRow(self.poll_multi_cb)
        pl.addLayout(pf)
        poll_btn = QPushButton("Create Poll")
        poll_btn.clicked.connect(self.create_poll)
        pl.addWidget(poll_btn)
        tabs.addTab(poll_tab, "Poll")

        # React tab
        react_tab = QWidget()
        rl = QVBoxLayout(react_tab)
        rf = QFormLayout()
        self.react_msgid = QLineEdit()
        self.react_msgid.setPlaceholderText("Message ID")
        rf.addRow("Msg ID:", self.react_msgid)
        self.react_emoji = QLineEdit()
        self.react_emoji.setPlaceholderText("Emoji (e.g. \U0001f44d)")
        rf.addRow("Emoji:", self.react_emoji)
        react_remove_cb = QCheckBox("Remove reaction")
        rf.addRow(react_remove_cb)
        rl.addLayout(rf)
        react_btn = QPushButton("React")
        react_btn.clicked.connect(self.react)
        rl.addWidget(react_btn)
        tabs.addTab(react_tab, "React")

        layout.addWidget(tabs)

        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        self.result_area.setFont(QFont("Consolas", 10))
        layout.addWidget(self.result_area, stretch=1)

    def _get_base_cmd(self):
        ch = self.channel_combo.currentText()
        target = self.target_input.text().strip()
        if not target:
            return None
        cmd = "Call message with action='send', channel='%s', target='%s'" % (ch, target)
        return cmd

    def send(self):
        cmd = self._get_base_cmd()
        if not cmd:
            QMessageBox.warning(self, "Warning", "Enter target")
            return
        msg = self.msg_input.toPlainText().strip()
        if not msg:
            QMessageBox.warning(self, "Warning", "Enter message")
            return
        cmd += ", message='%s'" % msg
        thread = self.thread_input.text().strip()
        if thread:
            cmd += ", threadId='%s'" % thread
        # Check checkboxes - read from UI
        if self.findChild(QCheckBox, ""):
            pass
        cmd += ". Return raw JSON."
        self.result_area.append('<span style="color:#8b949e">Sending...</span>')
        w = ToolWorker(cmd)
        w.result_ready.connect(lambda r: self.result_area.append('<span style="color:#3fb950">%s</span>' % _safe_html(r)))
        w.error_occurred.connect(lambda e: self.result_area.append('<span style="color:#f85149">%s</span>' % _safe_html(str(e))))
        w.start()

    def create_poll(self):
        q = self.poll_question.text().strip()
        opts = self.poll_options.text().strip()
        if not q or not opts:
            QMessageBox.warning(self, "Warning", "Enter question and options")
            return
        cmd = "Call message with action='send', channel='%s', target='%s', pollQuestion='%s', pollOption='%s', pollDurationHours=%d" % (
            self.channel_combo.currentText(),
            self.target_input.text().strip(),
            q, opts, self.poll_hours.value()
        )
        if self.poll_multi_cb.isChecked():
            cmd += ", pollMulti=true"
        cmd += ". Return raw JSON."
        self.result_area.append('<span style="color:#8b949e">Creating poll...</span>')
        w = ToolWorker(cmd)
        w.result_ready.connect(lambda r: self.result_area.append(_safe_html(r)))
        w.start()

    def react(self):
        mid = self.react_msgid.text().strip()
        emoji = self.react_emoji.text().strip()
        if not mid or not emoji:
            QMessageBox.warning(self, "Warning", "Enter message ID and emoji")
            return
        cmd = "Call message with action='send', messageId='%s', emoji='%s', remove=%s, channel='%s', target='%s'" % (
            mid, emoji, str(self.findChildren(QCheckBox)[2].isChecked() if len(self.findChildren(QCheckBox)) > 2 else False).lower(),
            self.channel_combo.currentText(), self.target_input.text().strip()
        )
        cmd += ". Return raw JSON."
        w = ToolWorker(cmd)
        w.result_ready.connect(lambda r: self.result_area.append(_safe_html(r)))
        w.start()


# ============================================================
# TasksPage - Full cron management
# ============================================================
class TasksPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.jobs_data = []
        self.init_ui()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(30000)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Task Scheduler (Cron)"))

        tabs = QTabWidget()

        # List tab
        list_tab = QWidget()
        ll = QVBoxLayout(list_tab)
        list_tb = QHBoxLayout()
        ref_btn = QPushButton("Refresh")
        ref_btn.clicked.connect(self.refresh)
        list_tb.addWidget(ref_btn)
        ll.addLayout(list_tb)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["Job ID", "Name", "Schedule", "Type", "Status", "Created", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        ll.addWidget(self.table, stretch=1)
        tabs.addTab(list_tab, "Jobs")

        # Add tab
        add_tab = QWidget()
        al = QVBoxLayout(add_tab)
        af = QFormLayout()
        self.add_name = QLineEdit()
        self.add_name.setPlaceholderText("Job name")
        af.addRow("Name:", self.add_name)
        self.add_type = QComboBox()
        self.add_type.addItems(["cron", "every", "at"])
        self.add_type.currentTextChanged.connect(self._on_sched_type_change)
        af.addRow("Type:", self.add_type)
        self.add_cron = QLineEdit("0 9 * * *")
        self.add_cron.setPlaceholderText("Cron expression (e.g. 0 9 * * *)")
        af.addRow("Cron Expr:", self.add_cron)
        self.add_interval = QSpinBox()
        self.add_interval.setRange(1, 99999)
        self.add_interval.setValue(3600000)
        self.add_interval.setSuffix(" ms")
        af.addRow("Interval:", self.add_interval)
        self.add_at = QLineEdit()
        self.add_at.setPlaceholderText("ISO timestamp (e.g. 2026-06-05T09:00:00+08:00)")
        af.addRow("At:", self.add_at)
        self.add_session_type = QComboBox()
        self.add_session_type.addItems(["main", "isolated"])
        af.addRow("Session:", self.add_session_type)
        self.add_msg = QLineEdit()
        self.add_msg.setPlaceholderText("Message / system event text")
        af.addRow("Message:", self.add_msg)
        al.addLayout(af)

        add_btn = QPushButton("Add Job")
        add_btn.clicked.connect(self.add_job)
        al.addWidget(add_btn)
        tabs.addTab(add_tab, "Add")

        # History tab
        hist_tab = QWidget()
        hl = QVBoxLayout(hist_tab)
        hist_row = QHBoxLayout()
        hist_row.addWidget(QLabel("Job ID:"))
        self.hist_jobid = QLineEdit()
        hist_row.addWidget(self.hist_jobid, stretch=1)
        hist_btn = QPushButton("Get History")
        hist_btn.clicked.connect(self.get_history)
        hist_row.addWidget(hist_btn)
        run_btn = QPushButton("Run Now")
        run_btn.clicked.connect(self.run_now)
        hist_row.addWidget(run_btn)
        hl.addLayout(hist_row)

        self.hist_area = QTextEdit()
        self.hist_area.setReadOnly(True)
        self.hist_area.setFont(QFont("Consolas", 10))
        hl.addWidget(self.hist_area, stretch=1)
        tabs.addTab(hist_tab, "History")

        layout.addWidget(tabs)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(80)
        self.log.setFont(QFont("Consolas", 9))
        layout.addWidget(self.log)
        self.refresh()

    def _on_sched_type_change(self, text):
        pass

    def refresh(self):
        self.log.append('<span style="color:#8b949e">[%s] Refreshing...</span>' % datetime.now().strftime("%H:%M:%S"))
        w = ToolWorker("Call cron with action='list', includeDisabled=True. Return ONLY a JSON array of all jobs.")
        w.result_ready.connect(self._loaded)
        w.error_occurred.connect(lambda e: self.log.append('<span style="color:#f85149">%s</span>' % _safe_html(str(e))))
        w.start()

    def _loaded(self, result):
        try:
            jobs = json.loads(_unwrap_json(result))
            if not isinstance(jobs, list):
                jobs = [jobs]
            self.jobs_data = [j for j in jobs if isinstance(j, dict)]
            self.table.setRowCount(len(self.jobs_data))
            for i, j in enumerate(self.jobs_data):
                jid = str(j.get("jobId", ""))
                name = str(j.get("name", ""))
                sched = j.get("schedule", {})
                if isinstance(sched, dict):
                    sched_str = sched.get("expr", "") or "every %sms" % sched.get("everyMs", "") or sched.get("at", "")
                    kind = sched.get("kind", "")
                else:
                    sched_str = str(sched)
                    kind = ""
                en = str(j.get("enabled", ""))
                created = str(j.get("createdAt", ""))
                self.table.setItem(i, 0, QTableWidgetItem(jid))
                self.table.setItem(i, 1, QTableWidgetItem(name))
                self.table.setItem(i, 2, QTableWidgetItem(sched_str))
                self.table.setItem(i, 3, QTableWidgetItem(kind))
                self.table.setItem(i, 4, QTableWidgetItem(en))
                self.table.setItem(i, 5, QTableWidgetItem(created))

                btn_widget = QWidget()
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(0, 0, 0, 0)
                for lbl, act in [("Toggle", "toggle"), ("Delete", "delete")]:
                    b = QPushButton(lbl)
                    b.setFixedWidth(50)
                    b.clicked.connect(lambda _, jid=jid, a=act, en=en: self._action(jid, a, en))
                    btn_layout.addWidget(b)
                self.table.setCellWidget(i, 6, btn_widget)
            self.log.append('<span style="color:#3fb950">Loaded %d jobs</span>' % len(self.jobs_data))
        except Exception:
            self.log.append('<span style="color:#d29922">Parse error</span>')

    def _action(self, jid, action, current_enabled):
        if action == "toggle":
            new_en = current_enabled != "True"
            cmd = "Call cron with action='update', jobId='%s', patch enabled=%s. Return JSON." % (jid, str(new_en).lower())
        elif action == "delete":
            r = QMessageBox.question(self, "Confirm", "Delete job %s?" % jid)
            if r != QMessageBox.StandardButton.Yes:
                return
            cmd = "Call cron with action='remove', jobId='%s'. Return JSON." % jid
        else:
            return
        w = ToolWorker(cmd)
        w.result_ready.connect(lambda _: self.refresh())
        w.start()

    def add_job(self):
        name = self.add_name.text().strip()
        msg = self.add_msg.text().strip()
        sched_type = self.add_type.currentText()
        session_type = self.add_session_type.currentText()

        if sched_type == "cron":
            expr = self.add_cron.text().strip()
            if not expr or not msg:
                QMessageBox.warning(self, "Warning", "Enter cron expression and message")
                return
            cmd = "Call cron with action='add', name='%s', schedule kind='cron' expr='%s', payload kind='systemEvent' text='%s', sessionTarget='%s', enabled=True. Return JSON." % (name, expr, msg, session_type)
        elif sched_type == "every":
            ms = self.add_interval.value()
            if not msg:
                QMessageBox.warning(self, "Warning", "Enter message")
                return
            cmd = "Call cron with action='add', name='%s', schedule kind='every' everyMs=%d, payload kind='systemEvent' text='%s', sessionTarget='%s', enabled=True. Return JSON." % (name, ms, msg, session_type)
        elif sched_type == "at":
            at = self.add_at.text().strip()
            if not at or not msg:
                QMessageBox.warning(self, "Warning", "Enter timestamp and message")
                return
            cmd = "Call cron with action='add', name='%s', schedule kind='at' at='%s', payload kind='systemEvent' text='%s', sessionTarget='%s', enabled=True. Return JSON." % (name, at, msg, session_type)
        else:
            return

        self.log.append('<span style="color:#8b949e">Adding job...</span>')
        w = ToolWorker(cmd)
        w.result_ready.connect(lambda r: (self.log.append('<span style="color:#3fb950">%s</span>' % _safe_html(r[:300])), self.refresh()))
        w.error_occurred.connect(lambda e: self.log.append('<span style="color:#f85149">%s</span>' % _safe_html(str(e))))
        w.start()

    def get_history(self):
        jid = self.hist_jobid.text().strip()
        if not jid:
            QMessageBox.warning(self, "Warning", "Enter Job ID")
            return
        w = ToolWorker("Call cron with action='runs', jobId='%s'. Return raw JSON." % jid)
        w.result_ready.connect(lambda r: self.hist_area.setPlainText(r[:5000]))
        w.start()

    def run_now(self):
        jid = self.hist_jobid.text().strip()
        if not jid:
            QMessageBox.warning(self, "Warning", "Enter Job ID")
            return
        w = ToolWorker("Call cron with action='run', jobId='%s'. Return raw JSON." % jid)
        w.result_ready.connect(lambda r: (self.hist_area.setPlainText("Run result: " + r), self.refresh()))
        w.start()


# ============================================================
# SkillsPage - Skill & Agent management
# ============================================================
class SkillsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Skills & Agents"))

        tabs = QTabWidget()

        # Agents tab
        agents_tab = QWidget()
        agl = QVBoxLayout(agents_tab)
        list_btn = QPushButton("List Available Agents")
        list_btn.clicked.connect(self.list_agents)
        agl.addWidget(list_btn)
        self.agents_area = QTextEdit()
        self.agents_area.setReadOnly(True)
        self.agents_area.setFont(QFont("Consolas", 10))
        agl.addWidget(self.agents_area, stretch=1)
        tabs.addTab(agents_tab, "Agents")

        # Install tab
        install_tab = QWidget()
        il = QVBoxLayout(install_tab)
        il.addWidget(QLabel("Install Skill"))
        inf = QFormLayout()
        self.skill_name = QLineEdit()
        self.skill_name.setPlaceholderText("Skill name (e.g. openai-whisper)")
        inf.addRow("Skill:", self.skill_name)
        il.addLayout(inf)
        install_btn = QPushButton("Install")
        install_btn.clicked.connect(self.install_skill)
        il.addWidget(install_btn)

        il.addWidget(QLabel("Install from ZIP"))
        zip_row = QHBoxLayout()
        self.zip_path = QLineEdit()
        self.zip_path.setPlaceholderText("Path to .zip file")
        zip_row.addWidget(self.zip_path, stretch=1)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_zip)
        zip_row.addWidget(browse_btn)
        il.addLayout(zip_row)
        zip_install_btn = QPushButton("Install from ZIP")
        zip_install_btn.clicked.connect(self.install_zip)
        il.addWidget(zip_install_btn)

        il.addWidget(QLabel("Environment"))
        env_btn = QPushButton("Check Environment")
        env_btn.clicked.connect(self.check_env)
        il.addWidget(env_btn)
        tabs.addTab(install_tab, "Install")

        # Find tab
        find_tab = QWidget()
        fl = QVBoxLayout(find_tab)
        find_row = QHBoxLayout()
        self.find_query = QLineEdit()
        self.find_query.setPlaceholderText("What do you need? (e.g. image generation)")
        find_row.addWidget(self.find_query, stretch=1)
        find_btn = QPushButton("Find Skills")
        find_btn.clicked.connect(self.find_skills)
        find_row.addWidget(find_btn)
        fl.addLayout(find_row)
        self.find_area = QTextEdit()
        self.find_area.setReadOnly(True)
        self.find_area.setFont(QFont("Consolas", 10))
        fl.addWidget(self.find_area, stretch=1)
        tabs.addTab(find_tab, "Find")

        layout.addWidget(tabs)
        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        self.result_area.setFont(QFont("Consolas", 10))
        self.result_area.setMaximumHeight(150)
        layout.addWidget(self.result_area)

    def list_agents(self):
        self.agents_area.append('<span style="color:#8b949e">Listing agents...</span>')
        w = ToolWorker("Call agents_list. Return raw JSON.")
        w.result_ready.connect(lambda r: self.agents_area.append(_safe_html(r)))
        w.error_occurred.connect(lambda e: self.agents_area.append('<span style="color:#f85149">%s</span>' % _safe_html(str(e))))
        w.start()

    def install_skill(self):
        name = self.skill_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Warning", "Enter skill name")
            return
        self.result_area.append('<span style="color:#8b949e">Installing %s...</span>' % name)
        w = ToolWorker("Call skillhub_install with action='install_skill', skillName='%s'. Return raw result." % name)
        w.result_ready.connect(lambda r: self.result_area.append(_safe_html(r)))
        w.error_occurred.connect(lambda e: self.result_area.append('<span style="color:#f85149">%s</span>' % _safe_html(str(e))))
        w.start()

    def _browse_zip(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select ZIP", "", "ZIP Files (*.zip)")
        if f:
            self.zip_path.setText(f)

    def install_zip(self):
        p = self.zip_path.text().strip()
        if not p or not Path(p).exists():
            QMessageBox.warning(self, "Warning", "Select a valid ZIP file")
            return
        self.result_area.append('<span style="color:#8b949e">Installing from %s...</span>' % p)
        w = ToolWorker("Call skillhub_install with action='install_skill_zip', zipPath='%s'. Return raw result." % p)
        w.result_ready.connect(lambda r: self.result_area.append(_safe_html(r)))
        w.error_occurred.connect(lambda e: self.result_area.append('<span style="color:#f85149">%s</span>' % _safe_html(str(e))))
        w.start()

    def check_env(self):
        self.result_area.append('<span style="color:#8b949e">Checking environment...</span>')
        w = ToolWorker("Call skillhub_install with action='check_env'. Return raw result.")
        w.result_ready.connect(lambda r: self.result_area.append(_safe_html(r)))
        w.start()

    def find_skills(self):
        q = self.find_query.text().strip()
        if not q:
            return
        self.find_area.append('<span style="color:#8b949e">Searching: %s...</span>' % q)
        w = ToolWorker("Search for available skills that can help with: %s. List skill names and descriptions." % q)
        w.result_ready.connect(lambda r: self.find_area.append(_safe_html(r)))
        w.start()


# ============================================================
# MemoryPage - Full memory management
# ============================================================
class MemoryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Memory & History"))

        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search query...")
        search_row.addWidget(self.search_input, stretch=1)

        scope_cb = QComboBox()
        scope_cb.addItems(["memory", "wiki", "all"])
        search_row.addWidget(scope_cb)

        for label, method in [
            ("Memory Search", "mem_search"),
            ("LCM Grep", "lcm_grep"),
            ("LCM Expand", "lcm_expand"),
        ]:
            b = QPushButton(label)
            b.clicked.connect(lambda _, m=method, s=scope_cb: self._search(m, s.currentText()))
            search_row.addWidget(b)
        layout.addLayout(search_row)

        # Local files
        local_row = QHBoxLayout()
        local_row.addWidget(QLabel("Local:"))
        ws = Path.home() / ".qclaw" / "workspace-ua58rsb93veqtxl7"
        for name, path in [
            ("MEMORY.md", ws / "MEMORY.md"),
            ("SOUL.md", ws / "SOUL.md"),
            ("USER.md", ws / "USER.md"),
            ("TOOLS.md", ws / "TOOLS.md"),
        ]:
            b = QPushButton(name)
            b.clicked.connect(lambda _, p=path: self._show_local(p))
            local_row.addWidget(b)
        today = datetime.now().strftime("%Y-%m-%d")
        td_btn = QPushButton(today + ".md")
        td_btn.clicked.connect(lambda: self._show_local(ws / "memory" / (today + ".md")))
        local_row.addWidget(td_btn)
        local_row.addStretch()
        layout.addLayout(local_row)

        # LCM describe
        desc_row = QHBoxLayout()
        desc_row.addWidget(QLabel("LCM ID:"))
        self.lcm_id_input = QLineEdit()
        self.lcm_id_input.setPlaceholderText("e.g. sum_xxx or file_xxx")
        desc_row.addWidget(self.lcm_id_input, stretch=1)
        desc_btn = QPushButton("Describe")
        desc_btn.clicked.connect(self._lcm_describe)
        desc_row.addWidget(desc_btn)
        layout.addLayout(desc_row)

        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        self.result_area.setFont(QFont("Consolas", 10))
        layout.addWidget(self.result_area, stretch=1)

    def _show_local(self, path):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                self.result_area.setPlainText("=== %s ===\n%s" % (path.name, f.read()[:8000]))
        except Exception as e:
            self.result_area.setPlainText("Error reading %s: %s" % (path, e))

    def _search(self, method, scope):
        q = self.search_input.text().strip()
        if not q:
            return
        if method == "mem_search":
            self.result_area.append('<span style="color:#8b949e">Memory search: %s...</span>' % q)
            w = ToolWorker("Call memory_search with query='%s', corpus='%s', maxResults=20. Return raw JSON." % (q, scope))
        elif method == "lcm_grep":
            self.result_area.append('<span style="color:#8b949e">LCM grep: %s...</span>' % q)
            w = ToolWorker("Call lcm_grep with pattern='%s', mode='full_text', limit=20. Return raw JSON with all fields." % q)
        elif method == "lcm_expand":
            self.result_area.append('<span style="color:#8b949e">LCM expand query: %s...</span>' % q)
            w = ToolWorker("Call lcm_expand_query with query='%s', prompt='Summarize all relevant context found for this query.', maxTokens=3000. Return full answer." % q)
        else:
            return
        w.result_ready.connect(lambda r: self.result_area.append(_safe_html(r)))
        w.error_occurred.connect(lambda e: self.result_area.append('<span style="color:#f85149">%s</span>' % _safe_html(str(e))))
        w.start()

    def _lcm_describe(self):
        lid = self.lcm_id_input.text().strip()
        if not lid:
            QMessageBox.warning(self, "Warning", "Enter LCM ID")
            return
        self.result_area.append('<span style="color:#8b949e">Describing %s...</span>' % lid)
        w = ToolWorker("Call lcm_describe with id='%s'. Return raw result." % lid)
        w.result_ready.connect(lambda r: self.result_area.append(_safe_html(r)))
        w.start()


# ============================================================
# FilesPage - File management
# ============================================================
class FilesPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_path = Path.home()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        row.addWidget(QLabel("Path:"))
        self.path_input = QLineEdit(str(self.current_path))
        row.addWidget(self.path_input, stretch=1)
        b = QPushButton("Browse")
        b.clicked.connect(self.browse)
        row.addWidget(b)
        up_btn = QPushButton("Up")
        up_btn.clicked.connect(self.go_up)
        row.addWidget(up_btn)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load)
        row.addWidget(refresh_btn)
        layout.addLayout(row)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Size", "Modified"])
        self.tree.doubleClicked.connect(self._on_dblclick)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._context_menu)
        layout.addWidget(self.tree, stretch=1)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMaximumHeight(200)
        self.preview.setFont(QFont("Consolas", 9))
        layout.addWidget(self.preview)
        self.load()

    def browse(self):
        d = QFileDialog.getExistingDirectory(self, "Select Folder")
        if d:
            self.path_input.setText(d)
            self.current_path = Path(d)
            self.load()

    def go_up(self):
        p = self.current_path.parent
        if str(p) != str(self.current_path):
            self.current_path = p
            self.path_input.setText(str(p))
            self.load()

    def load(self):
        self.tree.clear()
        try:
            self.current_path = Path(self.path_input.text())
        except Exception:
            return
        if not self.current_path.exists():
            return
        try:
            for item in sorted(self.current_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                sz = self._fmt(item.stat().st_size) if item.is_file() else "<DIR>"
                mt = datetime.fromtimestamp(item.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                icon_char = "\U0001f4c1" if item.is_dir() else "\U0001f4c4"
                self.tree.addTopLevelItem(QTreeWidgetItem(["%s %s" % (icon_char, item.name), sz, mt]))
        except PermissionError:
            pass

    def _on_dblclick(self, idx):
        name = idx.data()
        if name.startswith("\U0001f4c1"):
            folder_name = name[2:]
            self.current_path = self.current_path / folder_name
            self.path_input.setText(str(self.current_path))
            self.load()
        else:
            file_name = name[2:]
            p = self.current_path / file_name
            if p.is_file():
                try:
                    self.preview.setPlainText(open(p, "r", encoding="utf-8", errors="replace").read()[:5000])
                except Exception:
                    self.preview.setPlainText("(binary file)")

    def _context_menu(self, pos):
        menu = QMenu(self)
        item = self.tree.itemAt(pos)
        if item:
            open_action = menu.addAction("Open / Preview")
            path_action = menu.addAction("Copy Path")
            menu.addSeparator()
            delete_action = menu.addAction("Delete")
            action = menu.exec(self.tree.mapToGlobal(pos))
            if action == open_action:
                self._on_dblclick(item, 0)
            elif action == path_action:
                name = item.data()
                prefix = name[:2]
                QApplication.clipboard().setText(str(self.current_path / name[2:]))
            elif action == delete_action:
                name = item.data()[2:]
                r = QMessageBox.question(self, "Delete", "Delete %s?" % name)
                if r == QMessageBox.StandardButton.Yes:
                    p = self.current_path / name
                    p.unlink() if p.is_file() else None
                    self.load()

    def _fmt(self, sz):
        for u in ["B", "KB", "MB", "GB"]:
            if sz < 1024:
                return "%d %s" % (sz, u)
            sz //= 1024
        return "%d TB" % sz


# ============================================================
# ExecPage - Advanced command execution
# ============================================================
class ExecPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cmd_history = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        row.addWidget(QLabel("Command:"))
        self.cmd = QLineEdit()
        self.cmd.setPlaceholderText("Enter command...")
        self.cmd.returnPressed.connect(self.run)
        row.addWidget(self.cmd, stretch=1)

        opts = QHBoxLayout()
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 600)
        self.timeout_spin.setValue(60)
        self.timeout_spin.setSuffix("s")
        opts.addWidget(self.timeout_spin)
        elevated_cb = QCheckBox("Elevated")
        opts.addWidget(elevated_cb)
        bg_cb = QCheckBox("Background")
        opts.addWidget(bg_cb)
        pty_cb = QCheckBox("PTY")
        opts.addWidget(pty_cb)
        run_btn = QPushButton("Run")
        run_btn.clicked.connect(self.run)
        opts.addWidget(run_btn)
        layout.addLayout(row)
        layout.addLayout(opts)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Consolas", 10))
        layout.addWidget(self.output, stretch=1)

    def run(self):
        c = self.cmd.text().strip()
        if not c:
            return
        self.cmd_history.append(c)
        self.output.append('<span style="color:#58a6ff">[%s] $ %s</span>' % (datetime.now().strftime("%H:%M:%S"), _safe_html(c)))
        timeout = self.timeout_spin.value()
        try:
            r = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
            if r.stdout:
                self.output.append(_safe_html(r.stdout.rstrip()))
            if r.returncode != 0 and r.stderr:
                self.output.append('<span style="color:#f85149">%s</span>' % _safe_html(r.stderr.rstrip()))
            self.output.append('<span style="color:#8b949e">Exit code: %d</span>' % r.returncode)
        except subprocess.TimeoutExpired:
            self.output.append('<span style="color:#f85149">Timeout after %ds</span>' % timeout)
        except Exception as e:
            self.output.append('<span style="color:#f85149">%s</span>' % _safe_html(str(e)))


# ============================================================
# GatewayPage - Gateway configuration & management (NEW)
# ============================================================
class GatewayPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Gateway Management"))

        tabs = QTabWidget()

        # Config tab
        config_tab = QWidget()
        cl = QVBoxLayout(config_tab)
        get_btn = QPushButton("Get Full Config")
        get_btn.clicked.connect(self._get_config)
        cl.addWidget(get_btn)
        schema_row = QHBoxLayout()
        schema_row.addWidget(QLabel("Schema Path:"))
        self.schema_input = QLineEdit("models.providers")
        schema_row.addWidget(self.schema_input, stretch=1)
        schema_btn = QPushButton("Lookup")
        schema_btn.clicked.connect(self._lookup_schema)
        schema_row.addWidget(schema_btn)
        cl.addLayout(schema_row)
        self.config_area = QTextEdit()
        self.config_area.setReadOnly(True)
        self.config_area.setFont(QFont("Consolas", 10))
        cl.addWidget(self.config_area, stretch=1)
        tabs.addTab(config_tab, "Config")

        # Restart tab
        restart_tab = QWidget()
        rl = QVBoxLayout(restart_tab)
        rl.addWidget(QLabel("Restart Gateway"))
        restart_btn = QPushButton("Restart Gateway")
        restart_btn.setStyleSheet("background: #3d1f1f; color: #f85149;")
        restart_btn.clicked.connect(self._restart)
        rl.addWidget(restart_btn)
        update_btn = QPushButton("Update & Restart")
        update_btn.setStyleSheet("background: #3d1f1f; color: #f85149;")
        update_btn.clicked.connect(self._update)
        rl.addWidget(update_btn)
        tabs.addTab(restart_tab, "Restart")

        layout.addWidget(tabs)

        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        self.result_area.setMaximumHeight(100)
        self.result_area.setFont(QFont("Consolas", 10))
        layout.addWidget(self.result_area)

    def _get_config(self):
        self.config_area.append('<span style="color:#8b949e">Fetching config...</span>')
        w = ToolWorker("Call gateway with action='config.get'. Return raw JSON.")
        w.result_ready.connect(lambda r: self.config_area.setPlainText(r[:8000]))
        w.error_occurred.connect(lambda e: self.result_area.append('<span style="color:#f85149">%s</span>' % _safe_html(str(e))))
        w.start()

    def _lookup_schema(self):
        path = self.schema_input.text().strip()
        if not path:
            return
        self.config_area.append('<span style="color:#8b949e">Looking up schema: %s...</span>' % path)
        w = ToolWorker("Call gateway with action='config.schema.lookup', path='%s'. Return raw result." % path)
        w.result_ready.connect(lambda r: self.config_area.append(_safe_html(r)))
        w.start()

    def _restart(self):
        r = QMessageBox.question(self, "Confirm", "Restart Gateway? This will disconnect all sessions.")
        if r != QMessageBox.StandardButton.Yes:
            return
        self.result_area.append('<span style="color:#d29922">Restarting Gateway...</span>')
        w = ToolWorker("Call gateway with action='restart', note='AgentStudio triggered restart'. Return result.")
        w.result_ready.connect(lambda r: self.result_area.append(_safe_html(r)))
        w.start()

    def _update(self):
        r = QMessageBox.question(self, "Confirm", "Update Gateway and restart?")
        if r != QMessageBox.StandardButton.Yes:
            return
        self.result_area.append('<span style="color:#d29922">Updating...</span>')
        w = ToolWorker("Call gateway with action='update.run', note='AgentStudio triggered update'. Return result.")
        w.result_ready.connect(lambda r: self.result_area.append(_safe_html(r)))
        w.start()


# ============================================================
# MultiAgentPage - Multi-Agent collaboration (NEW)
# ============================================================
class MultiAgentPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_agents = {}  # id -> info
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Multi-Agent Collaboration"))

        tabs = QTabWidget()

        # Spawn tab
        spawn_tab = QWidget()
        spl = QVBoxLayout(spawn_tab)

        sf = QFormLayout()
        self.spawn_task_input = QTextEdit()
        self.spawn_task_input.setMaximumHeight(80)
        self.spawn_task_input.setPlaceholderText("Describe the task for the sub-agent...")
        sf.addRow("Task:", self.spawn_task_input)

        self.spawn_mode = QComboBox()
        self.spawn_mode.addItems(["run (one-shot)", "session (persistent)"])
        sf.addRow("Mode:", self.spawn_mode)

        self.spawn_agent = QComboBox()
        sf.addRow("Agent ID:", self.spawn_agent)
        load_agents_btn = QPushButton("Load Agents")
        load_agents_btn.clicked.connect(self._load_agents)
        sf.addRow("", load_agents_btn)

        self.spawn_model = QComboBox()
        self.spawn_model.addItems(["(default)"] + [m["id"] for m in API.list_models()])
        sf.addRow("Model:", self.spawn_model)
        spl.addLayout(sf)

        spawn_btn = QPushButton("Spawn Agent")
        spawn_btn.setStyleSheet("background: #1a3a1a; color: #3fb950; font-weight: bold;")
        spawn_btn.clicked.connect(self._spawn)
        spl.addWidget(spawn_btn)
        tabs.addTab(spawn_tab, "Spawn")

        # Monitor tab
        monitor_tab = QWidget()
        ml = QVBoxLayout(monitor_tab)
        self.agent_table = QTableWidget()
        self.agent_table.setColumnCount(5)
        self.agent_table.setHorizontalHeaderLabels(["ID", "Task", "Status", "Model", "Created"])
        self.agent_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.agent_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        ml.addWidget(self.agent_table, stretch=1)
        tabs.addTab(monitor_tab, "Monitor")

        # Coordinate tab
        coord_tab = QWidget()
        col = QVBoxLayout(coord_tab)
        coord_row = QHBoxLayout()
        coord_row.addWidget(QLabel("Agent ID:"))
        self.coord_id = QLineEdit()
        coord_row.addWidget(self.coord_id, stretch=1)
        steer_btn = QPushButton("Steer")
        steer_btn.clicked.connect(self._steer)
        coord_row.addWidget(steer_btn)
        kill_btn = QPushButton("Kill")
        kill_btn.setStyleSheet("background: #3d1f1f; color: #f85149;")
        kill_btn.clicked.connect(self._kill)
        coord_row.addWidget(kill_btn)
        col.addLayout(coord_row)

        self.steer_msg = QLineEdit()
        self.steer_msg.setPlaceholderText("Steering message for the agent...")
        col.addWidget(self.steer_msg)

        coord_send_btn = QPushButton("Send to Agent")
        coord_send_btn.clicked.connect(self._steer)
        col.addWidget(coord_send_btn)

        # Pipeline - Sequential multi-agent workflow
        pipeline_frame = QGroupBox("Pipeline (Sequential Workflow)")
        pl = QVBoxLayout(pipeline_frame)
        self.pipeline_tasks = QTextEdit()
        self.pipeline_tasks.setMaximumHeight(120)
        self.pipeline_tasks.setPlaceholderText("One task per line:\nTask 1 for Agent A\nTask 2 for Agent B\nTask 3 for Agent C")
        pl.addWidget(self.pipeline_tasks)
        pipe_btn = QPushButton("Run Pipeline")
        pipe_btn.clicked.connect(self._run_pipeline)
        pl.addWidget(pipe_btn)
        col.addWidget(pipeline_frame)
        tabs.addTab(coord_tab, "Coordinate")

        layout.addWidget(tabs)

        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        self.result_area.setFont(QFont("Consolas", 10))
        layout.addWidget(self.result_area, stretch=1)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh_agents)
        self.refresh_timer.start(10000)

    def _load_agents(self):
        w = ToolWorker("Call agents_list. Return raw JSON list.")
        w.result_ready.connect(self._agents_loaded)
        w.start()

    def _agents_loaded(self, result):
        try:
            agents = json.loads(_unwrap_json(result))
            if isinstance(agents, list):
                current = self.spawn_agent.currentText()
                self.spawn_agent.clear()
                self.spawn_agent.addItem("(default)")
                for a in agents:
                    if isinstance(a, dict):
                        self.spawn_agent.addItem(str(a.get("id", str(a))))
                    elif isinstance(a, str):
                        self.spawn_agent.addItem(a)
                idx = self.spawn_agent.findText(current)
                if idx >= 0:
                    self.spawn_agent.setCurrentIndex(idx)
        except Exception:
            pass

    def _spawn(self):
        task = self.spawn_task_input.toPlainText().strip()
        if not task:
            QMessageBox.warning(self, "Warning", "Enter a task")
            return
        mode = "run" if "one-shot" in self.spawn_mode.currentText() else "session"
        cmd = "Call sessions_spawn with task='%s', mode='%s', cleanup='keep', streamTo='parent'" % (task, mode)
        agent_id = self.spawn_agent.currentText()
        if agent_id and agent_id != "(default)":
            cmd += ", agentId='%s'" % agent_id
        model = self.spawn_model.currentText()
        if model != "(default)":
            cmd += ", model='%s'" % model
        cmd += ". Return raw result."

        self.result_area.append('<span style="color:#3fb950">Spawning agent: %s</span>' % _safe_html(task[:100]))
        w = ToolWorker(cmd)
        w.result_ready.connect(self._spawn_result)
        w.error_occurred.connect(lambda e: self.result_area.append('<span style="color:#f85149">Spawn failed: %s</span>' % _safe_html(str(e))))
        w.start()

    def _spawn_result(self, result):
        self.result_area.append('<span style="color:#3fb950">Spawn result: %s</span>' % _safe_html(result[:500]))
        # Refresh agent list
        self._refresh_agents()

    def _refresh_agents(self):
        w = ToolWorker("Call subagents with action='list'. Return ONLY a JSON array of active subagents with id, status, task summary.")
        w.result_ready.connect(self._agents_refreshed)
        w.start()

    def _agents_refreshed(self, result):
        try:
            agents = json.loads(_unwrap_json(result))
            if not isinstance(agents, list):
                agents = [agents]
            self.agent_table.setRowCount(len(agents))
            for i, a in enumerate(agents):
                if isinstance(a, dict):
                    self.agent_table.setItem(i, 0, QTableWidgetItem(str(a.get("id", ""))))
                    self.agent_table.setItem(i, 1, QTableWidgetItem(str(a.get("task", ""))))
                    self.agent_table.setItem(i, 2, QTableWidgetItem(str(a.get("status", ""))))
                    self.agent_table.setItem(i, 3, QTableWidgetItem(str(a.get("model", ""))))
                    self.agent_table.setItem(i, 4, QTableWidgetItem(str(a.get("createdAt", ""))))
        except Exception:
            pass

    def _steer(self):
        aid = self.coord_id.text().strip()
        msg = self.steer_msg.text().strip()
        if not aid or not msg:
            QMessageBox.warning(self, "Warning", "Enter Agent ID and message")
            return
        self.result_area.append('<span style="color:#d29922">Steering %s...</span>' % aid)
        w = ToolWorker("Call subagents with action='steer', target='%s', message='%s'. Return raw result." % (aid, msg))
        w.result_ready.connect(lambda r: self.result_area.append(_safe_html(r)))
        w.start()

    def _kill(self):
        aid = self.coord_id.text().strip()
        if not aid:
            QMessageBox.warning(self, "Warning", "Enter Agent ID")
            return
        r = QMessageBox.question(self, "Confirm", "Kill agent %s?" % aid)
        if r != QMessageBox.StandardButton.Yes:
            return
        self.result_area.append('<span style="color:#f85149">Killing %s...</span>' % aid)
        w = ToolWorker("Call subagents with action='kill', target='%s'. Return raw result." % aid)
        w.result_ready.connect(lambda r: (self.result_area.append(_safe_html(r)), self._refresh_agents()))
        w.start()

    def _run_pipeline(self):
        tasks_text = self.pipeline_tasks.toPlainText().strip()
        if not tasks_text:
            return
        tasks = [t.strip() for t in tasks_text.split("\n") if t.strip()]
        if not tasks:
            return
        self.result_area.append('<span style="color:#58a6ff">Starting pipeline with %d tasks...</span>' % len(tasks))
        # Run each task sequentially through agents
        for i, task in enumerate(tasks):
            self.result_area.append('<span style="color:#d29922">[Stage %d/%d] %s</span>' % (i+1, len(tasks), _safe_html(task[:80])))
        # Send all tasks as one combined request
        combined = "Execute the following tasks sequentially, one agent per task, passing results forward:\n\n"
        for i, task in enumerate(tasks):
            combined += "Stage %d: %s\n" % (i+1, task)
        w = ToolWorker(combined)
        w.result_ready.connect(lambda r: self.result_area.append('<span style="color:#3fb950">Pipeline complete:\n%s</span>' % _safe_html(r[:3000])))
        w.error_occurred.connect(lambda e: self.result_area.append('<span style="color:#f85149">Pipeline failed: %s</span>' % _safe_html(str(e))))
        w.start()


# ============================================================
# SnapshotPage - Screenshot & Canvas (NEW)
# ============================================================
class SnapshotPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Snapshot & Vision"))

        row = QHBoxLayout()
        for label, cmd in [
            ("Screen Capture", "Call browser with action='screenshot', type='png'. Return raw JSON with full base64 image data."),
            ("Snapshot Aria", "Call browser with action='snapshot', snapshotFormat='aria'. Return full result."),
            ("Snapshot AI", "Call browser with action='snapshot', snapshotFormat='ai'. Return full result."),
            ("Canvas Present", "Call canvas with action='present'. Return result."),
            ("Canvas Hide", "Call canvas with action='hide'. Return result."),
        ]:
            b = QPushButton(label)
            b.clicked.connect(lambda _, c=cmd: self._exec(c))
            row.addWidget(b)
        layout.addLayout(row)

        # Canvas URL
        canvas_row = QHBoxLayout()
        canvas_row.addWidget(QLabel("Canvas URL:"))
        self.canvas_url = QLineEdit()
        canvas_row.addWidget(self.canvas_url, stretch=1)
        nav_btn = QPushButton("Navigate")
        nav_btn.clicked.connect(self._canvas_navigate)
        canvas_row.addWidget(nav_btn)
        layout.addLayout(canvas_row)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self.image_label = QLabel("No image")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background: #161b22; border: 1px solid #30363d;")
        self.image_label.setMinimumHeight(200)
        splitter.addWidget(self.image_label)

        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        self.result_area.setFont(QFont("Consolas", 10))
        splitter.addWidget(self.result_area)
        layout.addWidget(splitter, stretch=1)

    def _exec(self, instruction):
        self.result_area.append('<span style="color:#8b949e">Executing...</span>')
        w = ToolWorker(instruction)
        if "screenshot" in instruction:
            w.result_ready.connect(self._show_image)
        else:
            w.result_ready.connect(lambda r: self.result_area.append(_safe_html(r)))
        w.error_occurred.connect(lambda e: self.result_area.append('<span style="color:#f85149">%s</span>' % _safe_html(str(e))))
        w.start()

    def _show_image(self, result):
        try:
            data = _unwrap_json(result)
            # Try to extract base64 image
            b64 = None
            for marker in ["base64,", "data:image/png;base64,", "data:image/jpeg;base64,"]:
                idx = data.find(marker)
                if idx >= 0:
                    start = idx + len(marker)
                    b64 = data[start:].strip().split('"')[0].split("'")[0].split("}")[0].split("\\")[0]
                    break
            if b64:
                img_data = base64.b64decode(b64[:2000000])
                img = QImage()
                img.loadFromData(img_data)
                pixmap = QPixmap.fromImage(img)
                self.image_label.setPixmap(pixmap.scaled(
                    self.image_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
                self.result_area.append('<span style="color:#3fb950">Image loaded (%d bytes)</span>' % len(img_data))
            else:
                self.result_area.append(_safe_html(data[:500]))
        except Exception as e:
            self.result_area.append('<span style="color:#d29922">Image parse error: %s</span>' % _safe_html(str(e)))

    def _canvas_navigate(self):
        url = self.canvas_url.text().strip()
        if url:
            w = ToolWorker("Call canvas with action='navigate', url='%s'. Return result." % url)
            w.result_ready.connect(lambda r: self.result_area.append(_safe_html(r)))
            w.start()


# ============================================================
# MainWindow
# ============================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Agent Studio V5")
        self.setMinimumSize(1200, 800)
        self.advanced_mode = False
        self.all_nav_items = [
            ("\U0001f4ac Chat", ChatPage()),
            ("\U0001f4cb Sessions", SessionsPage()),
            ("\U0001f310 Browser", BrowserPage()),
            ("\U0001f4e6 Skills", SkillsPage()),
            ("\U0001f4c5 Tasks", TasksPage()),
            ("\U0001f4bb Nodes", NodesPage()),
            ("\U0001f4e8 Messages", MessagePage()),
            ("\U0001f9e0 Memory", MemoryPage()),
            ("\U0001f4c1 Files", FilesPage()),
            ("\U0001f527 Exec", ExecPage()),
            ("\U0001f517 Gateway", GatewayPage()),
            ("\U0001f916 Multi-Agent", MultiAgentPage()),
            ("\U0001f4f7 Snapshot", SnapshotPage()),
        ]
        self.init_ui()
        self.apply_theme()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        ml = QHBoxLayout(central)
        ml.setContentsMargins(0, 0, 0, 0)

        sidebar = QFrame()
        sidebar.setFixedWidth(180)
        sidebar.setStyleSheet("background: #161b22;")
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(0)

        logo = QLabel("\U0001f916 Agent Studio")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet("color: #e6edf3; font-size: 15px; font-weight: bold; padding: 16px 0;")
        sl.addWidget(logo)

        self.nav_container = QWidget()
        self.nav_layout = QVBoxLayout(self.nav_container)
        self.nav_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_layout.setSpacing(0)
        sl.addWidget(self.nav_container, 1)

        self.pages = QStackedWidget()
        self.nav_btns = []
        for i, (name, page) in enumerate(self.all_nav_items):
            btn = QPushButton(name)
            btn.setStyleSheet("""
                QPushButton { background: transparent; color: #c9d1d9; border: none;
                           text-align: left; padding: 9px 16px; font-size: 12px; }
                QPushButton:hover { background: #21262d; }
                QPushButton:checked { background: #21262d; color: #e6edf3;
                                      border-left: 3px solid #58a6ff; }
            """)
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, idx=i: self._switch(idx))
            self.nav_layout.addWidget(btn)
            self.nav_btns.append(btn)
            self.pages.addWidget(page)

        sl.addStretch()

        self.adv_toggle = QPushButton("\U0001f527 Advanced Mode")
        self.adv_toggle.setStyleSheet("""
            QPushButton { background: transparent; color: #8b949e; border: none;
                       text-align: left; padding: 9px 16px; font-size: 11px; }
            QPushButton:hover { background: #21262d; color: #e6edf3; }
            QPushButton:checked { color: #58a6ff; }
        """)
        self.adv_toggle.setCheckable(True)
        self.adv_toggle.clicked.connect(self._toggle_advanced)
        sl.addWidget(self.adv_toggle)

        self.conn_label = QLabel("  " + ("\U0001f7e2 Connected" if API.base_url else "\U0001f534 No Gateway"))
        self.conn_label.setStyleSheet("color: #3fb950; font-size: 11px; padding: 8px 16px;")
        if not API.base_url:
            self.conn_label.setStyleSheet("color: #f85149; font-size: 11px; padding: 8px 16px;")
        sl.addWidget(self.conn_label)

        ml.addWidget(sidebar)
        ml.addWidget(self.pages, 1)

        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        self._apply_nav_visibility()
        self._switch(0)

    def _toggle_advanced(self, checked):
        self.advanced_mode = checked
        self._apply_nav_visibility()
        if not self.advanced_mode:
            self._switch(0)

    def _apply_nav_visibility(self):
        simple_visible = {0, 8}
        for i, btn in enumerate(self.nav_btns):
            btn.setVisible(self.advanced_mode or i in simple_visible)
        self.adv_toggle.setText(
            "\U0001f527 Simple Mode" if self.advanced_mode else "\U0001f527 Advanced Mode"
        )

    def _switch(self, idx):
        for i, b in enumerate(self.nav_btns):
            b.setChecked(i == idx)
        self.pages.setCurrentIndex(idx)

    def apply_theme(self):
        self.setStyleSheet("""
            QMainWindow { background: #0d1117; }
            QMenuBar { background: #161b22; color: #c9d1d9; }
            QMenuBar::item:selected { background: #21262d; }
            QMenu { background: #161b22; color: #c9d1d9; border: 1px solid #30363d; }
            QMenu::item:selected { background: #21262d; }
            QWidget { background: transparent; }
            QLabel { background: transparent; color: #e6edf3; }
            QGroupBox { color: #e6edf3; border: 1px solid #30363d; border-radius: 4px; margin-top: 8px; padding-top: 16px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QTextEdit { background: #161b22; color: #e6edf3; border: 1px solid #30363d; selection-background-color: #264f78; }
            QLineEdit { background: #161b22; color: #e6edf3; border: 1px solid #30363d; padding: 4px 8px; border-radius: 4px; }
            QPushButton { background: #21262d; color: #e6edf3; border: 1px solid #30363d; padding: 6px 12px; border-radius: 4px; }
            QPushButton:hover { background: #30363d; }
            QPushButton:pressed { background: #383e47; }
            QComboBox { background: #161b22; color: #e6edf3; border: 1px solid #30363d; padding: 4px 8px; border-radius: 4px; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView { background: #161b22; color: #e6edf3; selection-background-color: #264f78; }
            QSpinBox { background: #161b22; color: #e6edf3; border: 1px solid #30363d; padding: 4px; }
            QCheckBox { color: #e6edf3; spacing: 6px; }
            QCheckBox::indicator { width: 16px; height: 16px; }
            QTableWidget { background: #161b22; color: #e6edf3; border: 1px solid #30363d; gridline-color: #30363d; }
            QTableWidget::item:selected { background: #264f78; }
            QHeaderView::section { background: #21262d; color: #e6edf3; border: 1px solid #30363d; padding: 4px 8px; }
            QTreeWidget { background: #161b22; color: #e6edf3; border: 1px solid #30363d; }
            QTreeWidget::item:selected { background: #264f78; }
            QListWidget { background: #161b22; color: #e6edf3; border: 1px solid #30363d; }
            QListWidget::item:selected { background: #264f78; }
            QTabWidget::pane { border: 1px solid #30363d; background: #0d1117; }
            QTabBar::tab { background: #161b22; color: #8b949e; padding: 8px 16px; border: 1px solid #30363d; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #0d1117; color: #e6edf3; }
            QSplitter::handle { background: #30363d; height: 2px; }
            QScrollBar { background: #161b22; width: 8px; }
            QScrollBar::handle:vertical { background: #30363d; border-radius: 4px; min-height: 20px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QStatusBar { background: #161b22; color: #8b949e; }
        """)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
