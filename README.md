# Agent Studio V5 - 完整版

**一个功能完整的桌面智能体工作室**

[![Build Status](https://img.shields.io/github/actions/workflow/status/willy0615/agent-studio-build/build.yml?branch=master)](https://github.com/willy0615/agent-studio-build/actions)
[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.x-green)](https://riverbankcomputing.com/software/pyqt/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 🎯 项目简介

Agent Studio 是一个基于 PyQt6 的桌面应用，集成了：
- 💬 **聊天功能** - 通过 OpenClaw LLM API 进行对话
- 🖱️ **电脑操作** - 截屏 + 多模态 + pywinauto 自动化
- 📁 **文件管理** - 本地文件浏览、编辑、保存
- 📋 **任务调度** - 定时任务管理（调用 OpenClaw Cron API）
- 🌐 **浏览器自动化** - 网页操作自动化（调用 OpenClaw Browser API）
- 🔧 **技能调用** - 调用 OpenClav Skills（PDF/Excel/Word 等）
- 💻 **代码执行** - Shell 命令执行
- 🧠 **记忆系统** - 自动保存重要信息

---

## 📥 下载安装

### 方式1：下载 EXE（推荐）

1. 访问 [GitHub Actions](https://github.com/willy0615/agent-studio-build/actions)
2. 找到最新的成功构建（绿色 ✓）
3. 下载 `AgentStudio-V5` artifact
4. 解压后运行 `AgentStudio.exe`

### 方式2：从源码运行

```bash
# 克隆仓库
git clone https://github.com/willy0615/agent-studio-build.git
cd agent-studio-build

# 安装依赖
pip install PyQt6 requests pywinauto Pillow

# 运行
cd desktop_app
python main.py
```

---

## 🚀 功能介绍

### 1. 💬 聊天页面
- 直接输入问题，调用 OpenClaw LLM 回答
- 支持多轮对话，自动保存历史
- 点击「操作电脑」进入自动化模式

### 2. 📁 文件管理页面
- 左侧：目录树导航
- 右侧：文件内容编辑器
- 支持：新建、编辑、保存文件
- 自动保存到记忆系统

### 3. 📋 任务调度页面
- 三种调度类型：
  - **一次性 (at)** - 指定时间执行
  - **周期性 (every)** - 每隔 N 分钟执行
  - **Cron 表达式** - 灵活配置
- 功能：添加、删除、暂停、恢复任务
- 自动刷新任务状态（5秒间隔）

### 4. 🌐 浏览器自动化页面
- URL 导航 + 截图预览
- 操作类型：点击、输入、按键、滚动
- 操作历史记录
- 支持坐标定位和元素选择

### 5. 🔧 技能调用页面
- 技能列表展示
- 参数验证（JSON 格式检查）
- 结果实时显示
- 技能文档说明

### 6. 💻 代码执行页面
- 多语言支持：Python、Shell、JavaScript、PowerShell
- 语法高亮（Python）
- 超时控制（10-300秒）
- stdout/stderr 输出显示

### 7. 📊 统计页面
- API 调用次数统计
- Token 使用量统计
- 平均响应时间
- 历史使用趋势

### 8. ⚙️ 设置页面
- API URL 配置
- Auth Token 配置
- 配置保存到本地

---

## 🧠 记忆系统

Agent Studio 会自动记住重要信息：

### 长期记忆
- 路径：`~/.qclaw/workspace-xxx/MEMORY.md`
- 内容：重要决策、偏好设置、项目上下文
- 用途：启动时自动加载，作为对话上下文

### 每日日志
- 路径：`~/.qclaw/workspace-xxx/memory/YYYY-MM-DD.md`
- 内容：聊天记录、操作日志、任务创建
- 用途：追溯历史、问题排查

---

## 🔧 技术栈

| 组件 | 技术 |
|------|------|
| GUI | PyQt6 |
| HTTP | requests |
| 电脑操作 | pywinauto + ctypes |
| 截屏 | Pillow + mss |
| 打包 | PyInstaller |
| CI/CD | GitHub Actions |
| API | OpenClaw 本地服务 |

---

## 📖 API 说明

Agent Studio 调用 OpenClaw 本地 API（默认 `127.0.0.1:52402`）：

### 聊天 API
```python
POST /v1/chat/completions
{
  "model": "openclaw",
  "messages": [{"role": "user", "content": "你好"}],
  "temperature": 0.7,
  "max_tokens": 2048
}
```

### Cron API
```python
GET  /cron/list              # 列出任务
POST /cron/add               # 添加任务
DELETE /cron/remove/{job_id} # 删除任务
```

### Browser API
```python
POST /browser/open   {"url": "https://example.com"}
POST /browser/snapshot {"tab_id": "xxx"}
POST /browser/act    {"action": {"kind": "click", "x": 100, "y": 200}}
```

### Skills API
```python
GET  /skills/list                  # 列出技能
POST /skills/invoke/{skill_id}     # 调用技能
```

### Exec API
```python
POST /exec {"command": "ls -la", "cwd": "/home", "timeout": 60}
```

---

## 🔐 安全说明

- Auth Token 存储在本地 `~/.qclaw/openclaw.json`
- 不会上传任何数据到云端
- 所有 API 调用都在本地网络

---

## 🐛 已知问题

1. **远程后端 500 错误** - 独立问题，不影响本地功能
2. **API 依赖** - 需要验证 OpenClaw 是否提供所有 API 端点

---

## 📝 更新日志

### V5 (2026-06-04)
- ✅ 完整实现所有 5 个阶段功能
- ✅ 任务状态实时刷新（QTimer）
- ✅ 任务暂停/恢复功能
- ✅ 浏览器操作历史记录
- ✅ 技能参数验证
- ✅ 代码语法高亮
- ✅ 项目 README 文档
- ✅ GitHub Actions 自动构建

### V4 (2026-06-03)
- 🎨 PyQt6 桌面应用架构
- 💬 基础聊天功能
- 🖱️ 电脑操作功能

---

## 📄 License

MIT License

---

## 👨‍💻 作者

willy0615

---

## 🙏 致谢

- [PyQt6](https://riverbankcomputing.com/software/pyqt/)
- [OpenClaw](https://github.com/openclaw)
- [pywinauto](https://github.com/pywinauto/pywinauto)
