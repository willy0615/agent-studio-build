# AgentStudio.exe V5 完整实现计划（方案B）

## 目标
将 AgentStudio.exe 从"阉割版"升级到"完整版"，功能接近 OpenClaw 助手。

---

## 阶段划分（共5阶段，每阶段1天）

### 阶段1：记忆系统 + 文件管理（Day 1）
**目标**：添加记忆系统和文件管理能力

**功能清单**：
1. **记忆系统**
   - 添加 `MEMORY.md` 读写逻辑
   - 添加每日日志 `memory/YYYY-MM-DD.md`
   - 聊天时自动保存重要信息到记忆
   - 启动时加载历史记忆

2. **文件管理页面**
   - 侧边栏添加「文件」图标
   - 文件浏览（目录树 + 文件列表）
   - 文件读取（双击打开，显示内容）
   - 文件编辑（编辑框 + 保存按钮）
   - 调用 OpenClaw API 进行文件操作

**代码变更**：
- `main.py`：添加 `MemoryManager` 类
- `main.py`：添加 `FilesPage` 类
- `main.py`：更新 `MainWindow` 侧边栏（5个图标）

**编译**：GitHub Actions（避免本地 SIGKILL）

---

### 阶段2：真实任务调度（Day 2）
**目标**：将 TasksPage 从"假列表"改为"真实任务"

**功能清单**：
1. **任务调度集成**
   - 调用 OpenClaw cron API 创建定时任务
   - 任务状态实时更新（待执行/执行中/已完成）
   - 任务执行结果通知
   - 任务删除/暂停/恢复

2. **任务类型支持**
   - 一次性任务（at）
   - 周期任务（cron）
   - 延迟任务（every）

**代码变更**：
- `main.py`：重构 `TasksPage`
- `main.py`：添加 `CronAPI` 类（调用 OpenClaw cron API）

**编译**：GitHub Actions

---

### 阶段3：浏览器自动化（Day 3）
**目标**：添加浏览器自动化能力

**功能清单**：
1. **浏览器页面**
   - 侧边栏添加「浏览器」图标
   - URL 输入框 + 导航按钮
   - 截图按钮（调用 OpenClaw browser API）
   - 点击/填表按钮（指定坐标或元素）

2. **浏览器操作**
   - 调用 OpenClaw browser API（open/snapshot/act）
   - 截屏显示（实时预览）
   - 操作记录（点击/输入历史）

**代码变更**：
- `main.py`：添加 `BrowserPage` 类
- `main.py`：添加 `BrowserAPI` 类（调用 OpenClaw browser API）

**编译**：GitHub Actions

---

### 阶段4：技能调用（Day 4）
**目标**：AgentStudio.exe 能调用 OpenClaw Skill

**前置条件**：OpenClaw 需要暴露 Skill 调用 API（检查是否存在）

**功能清单**：
1. **技能页面**
   - 侧边栏添加「技能」图标
   - 技能列表（显示可用 Skill）
   - 技能调用（选择 Skill + 输入参数）
   - 调用结果展示

2. **技能集成**
   - 调用 OpenClaw Skill API
   - 支持常用 Skill（pdf、xlsx、docx、windows-computer-agent）
   - 技能执行状态显示

**代码变更**：
- `main.py`：添加 `SkillsPage` 类
- `main.py`：添加 `SkillAPI` 类（调用 OpenClaw Skill API）

**编译**：GitHub Actions

---

### 阶段5：代码执行 + 最终优化（Day 5）
**目标**：添加代码执行能力，最终测试和优化

**功能清单**：
1. **代码执行页面**
   - 侧边栏添加「代码」图标
   - 代码编辑器（支持 Python/Shell）
   - 执行按钮（调用 OpenClaw exec API）
   - 输出显示（stdout/stderr）

2. **最终优化**
   - UI 细节优化（布局、配色、字体）
   - 性能优化（减少卡顿）
   - 错误处理（友好提示）
   - 文档（README.md）

**代码变更**：
- `main.py`：添加 `CodePage` 类
- `main.py`：添加 `ExecAPI` 类（调用 OpenClaw exec API）
- `README.md`：使用文档

**编译**：GitHub Actions（最终版本）

---

## GitHub Actions 编译配置

### .github/workflows/build.yml
```yaml
name: Build AgentStudio.exe

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  build:
    runs-on: windows-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.12'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install pyinstaller PyQt6 requests pywinauto Pillow
    
    - name: Build with PyInstaller
      run: |
        cd desktop_app
        pyinstaller --onefile --windowed --name AgentStudio main.py
    
    - name: Upload artifact
      uses: actions/upload-artifact@v4
      with:
        name: AgentStudio
        path: desktop_app/dist/AgentStudio.exe
```

---

## 时间表

| 阶段 | 时间 | 功能 | 编译 |
|------|------|------|------|
| 1 | Day 1 | 记忆系统 + 文件管理 | GitHub Actions |
| 2 | Day 2 | 真实任务调度 | GitHub Actions |
| 3 | Day 3 | 浏览器自动化 | GitHub Actions |
| 4 | Day 4 | 技能调用 | GitHub Actions |
| 5 | Day 5 | 代码执行 + 优化 | GitHub Actions（最终版） |

---

## 风险与缓解

### 风险1：OpenClaw API 不支持某些功能
- **影响**：阶段3/4/5 可能无法实现
- **缓解**：检查 OpenClaw API 文档，或自己实现中间层

### 风险2：GitHub Actions 编译失败
- **影响**：无法生成 EXE
- **缓解**：检查日志，修复依赖问题

### 风险3：功能实现时间超出预期
- **影响**：5天无法完成
- **缓解**：分阶段交付，每阶段独立可用

---

## 立即开始

现在开始**阶段1：记忆系统 + 文件管理**

**步骤**：
1. 检查 OpenClaw API 是否支持文件操作
2. 添加 `MemoryManager` 类
3. 添加 `FilesPage` 类
4. 更新 `MainWindow` 侧边栏
5. 本地测试
6. 推送到 GitHub，触发编译
