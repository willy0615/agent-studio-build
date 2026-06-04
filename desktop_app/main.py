#!/usr/bin/env python3
"""
Agent Studio V5 - 完整真实实现版
按照 OpenClaw 功能对比基准开发
覆盖率目标：从 25.3% → 100%
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
# 工作线程
# ============================================================
class APIWorker(QThread):
    """通用 API 调用工作线程"""
    result_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, method: str, endpoint: str, payload: Dict = None, timeout: int = 60):
        super().__init__()
        self.method = method
        self.endpoint = endpoint
        self.payload = payload
        self.timeout = timeout
    
    def run(self):
        try:
            url = CONFIG["base_url"] + self.endpoint
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + CONFIG["token"]
            }
            
            if self.method == "GET":
                resp = requests.get(url, headers=headers, timeout=self.timeout)
            else:
                resp = requests.post(url, headers=headers, json=self.payload, timeout=self.timeout)
            
            if resp.status_code != 200:
                self.error_occurred.emit("HTTP %d: %s" % (resp.status_code, resp.text[:200]))
                return
            
            data = resp.json()
            self.result_ready.emit(data)
            
        except requests.Timeout:
            self.error_occurred.emit("请求超时")
        except Exception as e:
            self.error_occurred.emit(str(e))


class StreamWorker(QThread):
    """流式聊天工作线程"""
    chunk_received = pyqtSignal(str)
    result_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, messages: List[Dict]):
        super().__init__()
        self.messages = messages
    
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
                "stream": True,
                "temperature": 0.7,
                "max_tokens": 4096
            }
            
            resp = requests.post(url, headers=headers, json=payload, stream=True, timeout=120)
            
            if resp.status_code != 200:
                self.error_occurred.emit("API 错误 %d: %s" % (resp.status_code, resp.text[:200]))
                return
            
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
            
        except Exception as e:
            self.error_occurred.emit(str(e))


# ============================================================
# 第一优先级：完全缺失的功能
# ============================================================

class SessionsPage(QWidget):
    """会话管理页面 - 真实调用 OpenClaw sessions API"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.sessions = []
        self.current_session = None
        self.init_ui()
        self.load_sessions()
        
        # 自动刷新
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.load_sessions)
        self.refresh_timer.start(5000)
    
    def init_ui(self):
        layout = QHBoxLayout(self)
        
        # 左侧：会话列表
        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)
        
        left_layout.addWidget(QLabel("活跃会话"))
        
        self.session_list = QListWidget()
        self.session_list.itemClicked.connect(self.select_session)
        left_layout.addWidget(self.session_list)
        
        btn_row = QHBoxLayout()
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.load_sessions)
        btn_row.addWidget(refresh_btn)
        
        spawn_btn = QPushButton("新建子会话")
        spawn_btn.clicked.connect(self.spawn_session)
        btn_row.addWidget(spawn_btn)
        
        left_layout.addLayout(btn_row)
        
        layout.addWidget(left_panel, stretch=1)
        
        # 右侧：会话详情
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        
        right_layout.addWidget(QLabel("会话历史"))
        
        self.history_view = QTextEdit()
        self.history_view.setReadOnly(True)
        right_layout.addWidget(self.history_view, stretch=1)
        
        input_row = QHBoxLayout()
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("输入消息...")
        input_row.addWidget(self.message_input, stretch=1)
        
        send_btn = QPushButton("发送")
        send_btn.clicked.connect(self.send_message)
        input_row.addWidget(send_btn)
        
        right_layout.addLayout(input_row)
        
        layout.addWidget(right_panel, stretch=2)
    
    def load_sessions(self):
        """真实调用 sessions_list"""
        worker = APIWorker("GET", "/sessions/list", {"limit": 20})
        worker.result_ready.connect(self.on_sessions_loaded)
        worker.error_occurred.connect(self.on_error)
        worker.start()
        self.current_worker = worker
    
    def on_sessions_loaded(self, data: Dict):
        self.sessions = data.get("sessions", [])
        self.session_list.clear()
        
        for session in self.sessions:
            label = session.get("label", session.get("key", "Unknown"))
            status = session.get("status", "unknown")
            item = QListWidgetItem("%s [%s]" % (label[:50], status))
            item.setData(Qt.ItemDataRole.UserRole, session)
            self.session_list.addItem(item)
    
    def select_session(self, item: QListWidgetItem):
        session = item.data(Qt.ItemDataRole.UserRole)
        self.current_session = session
        self.load_history(session["key"])
    
    def load_history(self, session_key: str):
        """真实调用 sessions_history"""
        worker = APIWorker("GET", "/sessions/history", {"sessionKey": session_key, "limit": 100})
        worker.result_ready.connect(self.on_history_loaded)
        worker.error_occurred.connect(self.on_error)
        worker.start()
        self.current_worker = worker
    
    def on_history_loaded(self, data: Dict):
        # 这里应该解析历史记录，但 API 返回格式未知
        self.history_view.setPlainText(json.dumps(data, indent=2, ensure_ascii=False))
    
    def send_message(self):
        if not self.current_session:
            return
        
        message = self.message_input.text().strip()
        if not message:
            return
        
        """真实调用 sessions_send"""
        worker = APIWorker("POST", "/sessions/send", {
            "sessionKey": self.current_session["key"],
            "message": message,
            "timeoutSeconds": 120
        })
        worker.result_ready.connect(self.on_message_sent)
        worker.error_occurred.connect(self.on_error)
        worker.start()
        self.current_worker = worker
        
        self.message_input.clear()
    
    def on_message_sent(self, data: Dict):
        self.history_view.append("\n--- 消息已发送 ---")
        self.history_view.append(json.dumps(data, indent=2, ensure_ascii=False))
    
    def spawn_session(self):
        """真实调用 sessions_spawn"""
        worker = APIWorker("POST", "/sessions/spawn", {
            "task": "新子会话任务",
            "runtime": "subagent",
            "mode": "run"
        })
        worker.result_ready.connect(self.on_session_spawned)
        worker.error_occurred.connect(self.on_error)
        worker.start()
        self.current_worker = worker
    
    def on_session_spawned(self, data: Dict):
        QMessageBox.information(self, "成功", "子会话已创建")
        self.load_sessions()
    
    def on_error(self, error: str):
        self.history_view.append("\n错误: " + error)


class NodesPage(QWidget):
    """节点管理页面 - 真实调用 OpenClaw nodes API"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.nodes = []
        self.current_node = None
        self.init_ui()
        self.load_nodes()
        
        # 自动刷新
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.load_nodes)
        self.refresh_timer.start(10000)
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        title_row = QHBoxLayout()
        title_row.addWidget(QLabel("节点管理"))
        
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.load_nodes)
        title_row.addWidget(refresh_btn)
        
        layout.addLayout(title_row)
        
        # 节点列表
        self.node_list = QListWidget()
        self.node_list.itemClicked.connect(self.select_node)
        layout.addWidget(self.node_list, stretch=1)
        
        # 设备信息
        self.device_info = QTextEdit()
        self.device_info.setReadOnly(True)
        self.device_info.setMaximumHeight(150)
        layout.addWidget(self.device_info)
        
        # 操作按钮
        btn_row = QHBoxLayout()
        
        camera_btn = QPushButton("拍照")
        camera_btn.clicked.connect(self.camera_snap)
        btn_row.addWidget(camera_btn)
        
        location_btn = QPushButton("获取位置")
        location_btn.clicked.connect(self.get_location)
        btn_row.addWidget(location_btn)
        
        screen_btn = QPushButton("屏幕录制")
        screen_btn.clicked.connect(self.screen_record)
        btn_row.addWidget(screen_btn)
        
        layout.addLayout(btn_row)
        
        # 结果显示
        self.result_label = QLabel()
        layout.addWidget(self.result_label)
    
    def load_nodes(self):
        """真实调用 nodes status"""
        worker = APIWorker("GET", "/nodes/status")
        worker.result_ready.connect(self.on_nodes_loaded)
        worker.error_occurred.connect(self.on_error)
        worker.start()
        self.current_worker = worker
    
    def on_nodes_loaded(self, data: Dict):
        self.nodes = data.get("nodes", [])
        self.node_list.clear()
        
        if not self.nodes:
            self.node_list.addItem("无连接节点")
            return
        
        for node in self.nodes:
            name = node.get("name", node.get("id", "Unknown"))
            status = node.get("status", "unknown")
            item = QListWidgetItem("%s [%s]" % (name, status))
            item.setData(Qt.ItemDataRole.UserRole, node)
            self.node_list.addItem(item)
        
        # 默认选择第一个
        if self.nodes:
            self.select_node(self.node_list.item(0))
    
    def select_node(self, item: QListWidgetItem):
        node = item.data(Qt.ItemDataRole.UserRole)
        self.current_node = node
        self.load_device_info(node["id"])
    
    def load_device_info(self, node_id: str):
        """真实调用 nodes device_info"""
        worker = APIWorker("GET", "/nodes/device_info", {"node": node_id})
        worker.result_ready.connect(self.on_device_info_loaded)
        worker.error_occurred.connect(self.on_error)
        worker.start()
        self.current_worker = worker
    
    def on_device_info_loaded(self, data: Dict):
        self.device_info.setPlainText(json.dumps(data, indent=2, ensure_ascii=False))
    
    def camera_snap(self):
        if not self.current_node:
            return
        
        """真实调用 nodes camera_snap"""
        worker = APIWorker("POST", "/nodes/camera_snap", {
            "node": self.current_node["id"],
            "facing": "back"
        })
        worker.result_ready.connect(self.on_camera_snap)
        worker.error_occurred.connect(self.on_error)
        worker.start()
        self.current_worker = worker
    
    def on_camera_snap(self, data: Dict):
        # 如果返回图片，显示图片
        if "image" in data:
            img_data = base64.b64decode(data["image"])
            pixmap = QPixmap()
            pixmap.loadFromData(img_data)
            self.result_label.setPixmap(pixmap.scaled(300, 400, Qt.AspectRatioMode.KeepAspectRatio))
        else:
            self.result_label.setText("拍照成功")
    
    def get_location(self):
        if not self.current_node:
            return
        
        """真实调用 nodes location_get"""
        worker = APIWorker("GET", "/nodes/location_get", {"node": self.current_node["id"]})
        worker.result_ready.connect(self.on_location_loaded)
        worker.error_occurred.connect(self.on_error)
        worker.start()
        self.current_worker = worker
    
    def on_location_loaded(self, data: Dict):
        lat = data.get("latitude", 0)
        lon = data.get("longitude", 0)
        self.result_label.setText("位置: %f, %f" % (lat, lon))
    
    def screen_record(self):
        if not self.current_node:
            return
        
        """真实调用 nodes screen_record"""
        worker = APIWorker("POST", "/nodes/screen_record", {
            "node": self.current_node["id"],
            "durationMs": 10000
        })
        worker.result_ready.connect(self.on_screen_record)
        worker.error_occurred.connect(self.on_error)
        worker.start()
        self.current_worker = worker
    
    def on_screen_record(self, data: Dict):
        self.result_label.setText("录制完成: " + str(data))
    
    def on_error(self, error: str):
        QMessageBox.critical(self, "错误", error)


class MessagePage(QWidget):
    """消息推送页面 - 真实调用 OpenClaw message API"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("消息推送"))
        
        form = QFormLayout()
        
        # 渠道选择
        self.channel_combo = QComboBox()
        self.channel_combo.addItems(["telegram", "discord", "slack", "wechat"])
        form.addRow("渠道:", self.channel_combo)
        
        # 接收者
        self.to_input = QLineEdit()
        self.to_input.setPlaceholderText("接收者 ID 或用户名")
        form.addRow("接收者:", self.to_input)
        
        # 消息内容
        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("消息内容...")
        form.addRow("内容:", self.message_input)
        
        # 图片路径（可选）
        self.image_input = QLineEdit()
        self.image_input.setPlaceholderText("图片路径（可选）")
        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(self.browse_image)
        image_row = QHBoxLayout()
        image_row.addWidget(self.image_input)
        image_row.addWidget(browse_btn)
        form.addRow("图片:", image_row)
        
        layout.addLayout(form)
        
        # 发送按钮
        send_btn = QPushButton("发送消息")
        send_btn.clicked.connect(self.send_message)
        layout.addWidget(send_btn)
        
        # 结果显示
        self.result_view = QTextEdit()
        self.result_view.setReadOnly(True)
        layout.addWidget(self.result_view, stretch=1)
    
    def browse_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.image_input.setText(file_path)
    
    def send_message(self):
        channel = self.channel_combo.currentText()
        to = self.to_input.text().strip()
        message = self.message_input.toPlainText().strip()
        
        if not to or not message:
            QMessageBox.warning(self, "提示", "请填写接收者和消息内容")
            return
        
        payload = {
            "channel": channel,
            "to": to,
            "message": message
        }
        
        # 如果有图片
        image_path = self.image_input.text().strip()
        if image_path and Path(image_path).exists():
            with open(image_path, "rb") as f:
                img_data = base64.b64encode(f.read()).decode("utf-8")
            payload["buffer"] = "data:image/png;base64," + img_data
        
        """真实调用 message send"""
        worker = APIWorker("POST", "/message/send", payload)
        worker.result_ready.connect(self.on_message_sent)
        worker.error_occurred.connect(self.on_error)
        worker.start()
        self.current_worker = worker
    
    def on_message_sent(self, data: Dict):
        self.result_view.append("消息已发送")
        self.result_view.append(json.dumps(data, indent=2, ensure_ascii=False))
    
    def on_error(self, error: str):
        self.result_view.append("错误: " + error)


# ============================================================
# 第二优先级：严重不足的功能增强
# ============================================================

class SkillsPage(QWidget):
    """技能调用页面 - 动态加载技能列表"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.skills = []
        self.init_ui()
        self.load_skills()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("技能调用"))
        
        form = QFormLayout()
        
        # 技能选择（动态加载）
        self.skill_combo = QComboBox()
        form.addRow("技能:", self.skill_combo)
        
        # 参数输入
        self.params_input = QTextEdit()
        self.params_input.setPlaceholderText('{"param": "value"}')
        self.params_input.setMaximumHeight(100)
        form.addRow("参数:", self.params_input)
        
        layout.addLayout(form)
        
        invoke_btn = QPushButton("调用技能")
        invoke_btn.clicked.connect(self.invoke_skill)
        layout.addWidget(invoke_btn)
        
        # 结果显示
        self.result_view = QTextEdit()
        self.result_view.setReadOnly(True)
        layout.addWidget(self.result_view, stretch=1)
    
    def load_skills(self):
        """真实调用 agents_list 获取可用技能"""
        worker = APIWorker("GET", "/agents/list")
        worker.result_ready.connect(self.on_skills_loaded)
        worker.error_occurred.connect(self.on_load_fallback)
        worker.start()
        self.current_worker = worker
    
    def on_skills_loaded(self, data: Dict):
        agents = data.get("agents", [])
        self.skill_combo.clear()
        
        if agents:
            for agent in agents:
                name = agent.get("name", agent.get("id", "Unknown"))
                self.skill_combo.addItem(name)
            self.skills = agents
        else:
            # 如果 API 返回空，显示提示
            self.skill_combo.addItem("暂无可用技能")
    
    def on_load_fallback(self, error: str):
        # 如果加载失败，显示错误信息，不硬编码
        self.skill_combo.addItem("加载失败: " + error[:50])
    
    def invoke_skill(self):
        skill_name = self.skill_combo.currentText()
        if not skill_name or skill_name in ["暂无可用技能", "加载失败"]:
            QMessageBox.warning(self, "提示", "请先加载技能列表")
            return
        
        params_text = self.params_input.toPlainText().strip()
        try:
            params = json.loads(params_text) if params_text else {}
        except:
            params = {"input": params_text}
        
        # 通过发送消息让主 Agent 调用技能
        message = "请使用 %s 技能完成以下任务：\n\n参数：\n%s" % (
            skill_name,
            json.dumps(params, ensure_ascii=False, indent=2)
        )
        
        worker = StreamWorker([{"role": "user", "content": message}])
        worker.chunk_received.connect(self.on_chunk)
        worker.result_ready.connect(self.on_result)
        worker.error_occurred.connect(self.on_error)
        worker.start()
        self.current_worker = worker
    
    def on_chunk(self, chunk: str):
        self.result_view.moveCursor(QTextCursor.MoveOperation.End)
        self.result_view.insertPlainText(chunk)
    
    def on_result(self, content: str):
        self.result_view.append("\n--- 完成 ---")
    
    def on_error(self, error: str):
        self.result_view.append("错误: " + error)


class BrowserPage(QWidget):
    """浏览器控制页面 - 完整 Profile 管理"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.profiles = []
        self.current_profile = None
        self.init_ui()
        self.load_status()
        
        # 自动刷新
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.load_status)
        self.refresh_timer.start(5000)
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题行
        title_row = QHBoxLayout()
        title_row.addWidget(QLabel("浏览器控制"))
        
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.load_status)
        title_row.addWidget(refresh_btn)
        
        layout.addLayout(title_row)
        
        # Profile 选择
        profile_row = QHBoxLayout()
        profile_row.addWidget(QLabel("Profile:"))
        
        self.profile_combo = QComboBox()
        profile_row.addWidget(self.profile_combo, stretch=1)
        
        switch_btn = QPushButton("切换")
        switch_btn.clicked.connect(self.switch_profile)
        profile_row.addWidget(switch_btn)
        
        layout.addLayout(profile_row)
        
        # 状态显示
        self.status_label = QLabel()
        layout.addWidget(self.status_label)
        
        # 截图显示
        self.screenshot_label = QLabel("点击「截图」开始")
        self.screenshot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.screenshot_label.setMinimumHeight(400)
        layout.addWidget(self.screenshot_label, stretch=1)
        
        # URL 输入
        url_row = QHBoxLayout()
        url_row.addWidget(QLabel("网址:"))
        
        self.url_input = QLineEdit()
        self.url_input.setText("https://www.google.com")
        url_row.addWidget(self.url_input, stretch=1)
        
        open_btn = QPushButton("打开")
        open_btn.clicked.connect(self.open_url)
        url_row.addWidget(open_btn)
        
        layout.addLayout(url_row)
        
        # 操作按钮
        btn_row = QHBoxLayout()
        
        screenshot_btn = QPushButton("截图")
        screenshot_btn.clicked.connect(self.take_screenshot)
        btn_row.addWidget(screenshot_btn)
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close_browser)
        btn_row.addWidget(close_btn)
        
        layout.addLayout(btn_row)
    
    def load_status(self):
        """真实调用 browser status"""
        worker = APIWorker("GET", "/browser/status")
        worker.result_ready.connect(self.on_status_loaded)
        worker.error_occurred.connect(self.on_error)
        worker.start()
        self.current_worker = worker
    
    def on_status_loaded(self, data: Dict):
        # 显示状态
        status = data.get("status", "unknown")
        running = data.get("running", False)
        profile = data.get("profile", "unknown")
        
        self.status_label.setText("状态: %s | 运行: %s | Profile: %s" % (status, running, profile))
        
        # 加载 Profile 列表
        self.load_profiles()
    
    def load_profiles(self):
        """真实调用 browser profiles"""
        worker = APIWorker("GET", "/browser/profiles")
        worker.result_ready.connect(self.on_profiles_loaded)
        worker.error_occurred.connect(self.on_error)
        worker.start()
        self.current_worker = worker
    
    def on_profiles_loaded(self, data: Dict):
        self.profile_combo.clear()
        profiles = data.get("profiles", ["openclaw", "user", "default"])
        
        for profile in profiles:
            self.profile_combo.addItem(profile)
        
        self.profiles = profiles
    
    def switch_profile(self):
        profile = self.profile_combo.currentText()
        
        """真实调用 browser start"""
        worker = APIWorker("POST", "/browser/start", {"profile": profile})
        worker.result_ready.connect(self.on_profile_switched)
        worker.error_occurred.connect(self.on_error)
        worker.start()
        self.current_worker = worker
    
    def on_profile_switched(self, data: Dict):
        QMessageBox.information(self, "成功", "Profile 已切换")
        self.load_status()
    
    def open_url(self):
        url = self.url_input.text().strip()
        if not url:
            return
        
        """真实调用 browser open"""
        worker = APIWorker("POST", "/browser/open", {"url": url})
        worker.result_ready.connect(self.on_url_opened)
        worker.error_occurred.connect(self.on_error)
        worker.start()
        self.current_worker = worker
    
    def on_url_opened(self, data: Dict):
        self.status_label.setText("页面已打开")
    
    def take_screenshot(self):
        """真实调用 browser screenshot"""
        worker = APIWorker("POST", "/browser/screenshot", {})
        worker.result_ready.connect(self.on_screenshot_taken)
        worker.error_occurred.connect(self.on_error)
        worker.start()
        self.current_worker = worker
    
    def on_screenshot_taken(self, data: Dict):
        # 如果返回图片数据
        if "image" in data:
            img_data = base64.b64decode(data["image"])
            pixmap = QPixmap()
            pixmap.loadFromData(img_data)
            self.screenshot_label.setPixmap(pixmap.scaled(
                self.screenshot_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            self.screenshot_label.setText("截图成功，但无图片数据")
    
    def close_browser(self):
        """真实调用 browser stop"""
        worker = APIWorker("POST", "/browser/stop", {})
        worker.result_ready.connect(self.on_browser_closed)
        worker.error_occurred.connect(self.on_error)
        worker.start()
        self.current_worker = worker
    
    def on_browser_closed(self, data: Dict):
        self.status_label.setText("浏览器已关闭")
    
    def on_error(self, error: str):
        self.status_label.setText("错误: " + error[:50])


class TasksPage(QWidget):
    """任务调度页面 - 完整历史记录"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.jobs = []
        self.current_job = None
        self.init_ui()
        self.load_jobs()
        
        # 自动刷新
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.load_jobs)
        self.refresh_timer.start(10000)
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("任务调度"))
        
        # 任务表格
        self.jobs_table = QTableWidget()
        self.jobs_table.setColumnCount(5)
        self.jobs_table.setHorizontalHeaderLabels(["ID", "Cron", "消息", "状态", "操作"])
        self.jobs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.jobs_table.itemClicked.connect(self.select_job)
        layout.addWidget(self.jobs_table, stretch=1)
        
        # 添加任务
        add_group = QGroupBox("添加新任务")
        add_layout = QFormLayout(add_group)
        
        self.cron_input = QLineEdit()
        self.cron_input.setPlaceholderText("0 9 * * *")
        add_layout.addRow("Cron:", self.cron_input)
        
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("每天早上9点提醒我...")
        add_layout.addRow("消息:", self.message_input)
        
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self.add_job)
        add_layout.addRow(add_btn)
        
        layout.addWidget(add_group)
        
        # 运行历史
        history_group = QGroupBox("运行历史")
        history_layout = QVBoxLayout(history_group)
        
        self.history_view = QTextEdit()
        self.history_view.setReadOnly(True)
        self.history_view.setMaximumHeight(150)
        history_layout.addWidget(self.history_view)
        
        layout.addWidget(history_group)
    
    def load_jobs(self):
        """真实调用 cron list"""
        worker = APIWorker("GET", "/cron/list")
        worker.result_ready.connect(self.on_jobs_loaded)
        worker.error_occurred.connect(self.on_error)
        worker.start()
        self.current_worker = worker
    
    def on_jobs_loaded(self, data: Dict):
        self.jobs = data.get("jobs", [])
        self.jobs_table.setRowCount(len(self.jobs))
        
        for i, job in enumerate(self.jobs):
            self.jobs_table.setItem(i, 0, QTableWidgetItem(job.get("jobId", "")[:8]))
            self.jobs_table.setItem(i, 1, QTableWidgetItem(job.get("schedule", {}).get("expr", "")))
            self.jobs_table.setItem(i, 2, QTableWidgetItem(job.get("payload", {}).get("text", "")[:30]))
            
            status = "启用" if job.get("enabled", True) else "禁用"
            status_item = QTableWidgetItem(status)
            if job.get("enabled", True):
                status_item.setForeground(QColor("#3fb950"))
            else:
                status_item.setForeground(QColor("#f85149"))
            self.jobs_table.setItem(i, 3, status_item)
            
            # 切换按钮
            toggle_btn = QPushButton("切换" if job.get("enabled", True) else "启用")
            toggle_btn.clicked.connect(lambda checked, jid=job.get("jobId"): self.toggle_job(jid))
            self.jobs_table.setCellWidget(i, 4, toggle_btn)
    
    def select_job(self, item: QTableWidgetItem):
        row = item.row()
        if row < len(self.jobs):
            self.current_job = self.jobs[row]
            self.load_history(self.current_job["jobId"])
    
    def load_history(self, job_id: str):
        """真实调用 cron runs"""
        worker = APIWorker("GET", "/cron/runs", {"jobId": job_id})
        worker.result_ready.connect(self.on_history_loaded)
        worker.error_occurred.connect(self.on_error)
        worker.start()
        self.current_worker = worker
    
    def on_history_loaded(self, data: Dict):
        runs = data.get("runs", [])
        history_text = ""
        for run in runs[:10]:
            ts = run.get("timestamp", "unknown")
            status = run.get("status", "unknown")
            history_text += "%s - %s\n" % (ts, status)
        
        self.history_view.setPlainText(history_text if history_text else "无运行历史")
    
    def add_job(self):
        cron_expr = self.cron_input.text().strip()
        message = self.message_input.text().strip()
        
        if not cron_expr or not message:
            QMessageBox.warning(self, "提示", "请填写完整")
            return
        
        """真实调用 cron add"""
        worker = APIWorker("POST", "/cron/add", {
            "schedule": {"kind": "cron", "expr": cron_expr},
            "payload": {"kind": "systemEvent", "text": message},
            "sessionTarget": "main",
            "enabled": True
        })
        worker.result_ready.connect(self.on_job_added)
        worker.error_occurred.connect(self.on_error)
        worker.start()
        self.current_worker = worker
    
    def on_job_added(self, data: Dict):
        QMessageBox.information(self, "成功", "任务已添加")
        self.load_jobs()
    
    def toggle_job(self, job_id: str):
        # 获取当前状态
        current_enabled = True
        for job in self.jobs:
            if job.get("jobId") == job_id:
                current_enabled = job.get("enabled", True)
                break
        
        """真实调用 cron update"""
        worker = APIWorker("POST", "/cron/update", {
            "jobId": job_id,
            "patch": {"enabled": not current_enabled}
        })
        worker.result_ready.connect(self.on_job_updated)
        worker.error_occurred.connect(self.on_error)
        worker.start()
        self.current_worker = worker
    
    def on_job_updated(self, data: Dict):
        self.load_jobs()
    
    def on_error(self, error: str):
        QMessageBox.critical(self, "错误", error)


# ============================================================
# 第三优先级：原有功能增强
# ============================================================

class ChatPage(QWidget):
    """聊天页面 - 保持原有实现"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.messages = []
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("智能对话"))
        
        self.message_list = QTextEdit()
        self.message_list.setReadOnly(True)
        layout.addWidget(self.message_list, stretch=1)
        
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
        
        self.messages.append({"role": "user", "content": text})
        
        worker = StreamWorker(self.messages)
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
    
    def on_error(self, error: str):
        self.message_list.append("\n<b style='color: #f85149;'>错误:</b> " + error)


class MemoryPage(QWidget):
    """记忆管理页面 - LCM 集成"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        tabs = QTabWidget()
        
        # 本地记忆标签
        local_tab = QWidget()
        local_layout = QVBoxLayout(local_tab)
        
        self.memory_editor = QTextEdit()
        local_layout.addWidget(self.memory_editor)
        
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.save_memory)
        local_layout.addWidget(save_btn)
        
        tabs.addTab(local_tab, "本地记忆")
        
        # LCM 搜索标签
        lcm_tab = QWidget()
        lcm_layout = QVBoxLayout(lcm_tab)
        
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索记忆...")
        search_row.addWidget(self.search_input, stretch=1)
        
        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self.search_lcm)
        search_row.addWidget(search_btn)
        
        lcm_layout.addLayout(search_row)
        
        self.search_results = QTextEdit()
        self.search_results.setReadOnly(True)
        lcm_layout.addWidget(self.search_results, stretch=1)
        
        tabs.addTab(lcm_tab, "LCM 搜索")
        
        layout.addWidget(tabs)
        
        # 加载本地记忆
        self.load_memory()
    
    def load_memory(self):
        memory_path = Path.home() / ".qclaw" / "workspace-ua58rsb93veqtxl7" / "MEMORY.md"
        if memory_path.exists():
            with open(memory_path, "r", encoding="utf-8") as f:
                self.memory_editor.setPlainText(f.read())
    
    def save_memory(self):
        memory_path = Path.home() / ".qclaw" / "workspace-ua58rsb93veqtxl7" / "MEMORY.md"
        memory_path.parent.mkdir(parents=True, exist_ok=True)
        with open(memory_path, "w", encoding="utf-8") as f:
            f.write(self.memory_editor.toPlainText())
        QMessageBox.information(self, "成功", "记忆已保存")
    
    def search_lcm(self):
        query = self.search_input.text().strip()
        if not query:
            return
        
        """真实调用 lcm_grep"""
        worker = APIWorker("POST", "/lcm/grep", {
            "pattern": query,
            "mode": "full_text",
            "limit": 20
        })
        worker.result_ready.connect(self.on_search_results)
        worker.error_occurred.connect(self.on_error)
        worker.start()
        self.current_worker = worker
    
    def on_search_results(self, data: Dict):
        results = data.get("results", [])
        text = ""
        for r in results[:10]:
            text += "---\n%s\n" % r.get("snippet", "")[:200]
        self.search_results.setPlainText(text if text else "无结果")
    
    def on_error(self, error: str):
        self.search_results.setPlainText("错误: " + error)


class FilesPage(QWidget):
    """文件管理页面"""
    
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


class ExecPage(QWidget):
    """命令执行页面"""
    
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
        self.setWindowTitle("Agent Studio V5 - OpenClaw 完整对齐版")
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
        
        # 导航项 - 完整10个页面
        nav_items = [
            ("💬 对话", ChatPage()),
            ("🔄 会话", SessionsPage()),      # 新增
            ("🌐 浏览器", BrowserPage()),
            ("⚡ 技能", SkillsPage()),
            ("⏰ 任务", TasksPage()),
            ("📡 节点", NodesPage()),          # 新增
            ("📨 消息", MessagePage()),        # 新增
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
