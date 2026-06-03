# Agent系统增强方案

## 当前系统能力评估

### 已有功能 ✅
1. 多模式执行（Simple/ReAct/Multi）
2. RAG知识库
3. 工具调用（9个工具）
4. 自我反思
5. 学习机制
6. 多轮记忆压缩
7. 统计追踪

### 待增强方向 📈

---

## 一、能力增强

### 1. 🎯 视觉能力（多模态）
**价值**: 支持图像理解、图表分析

**实现方案**:
```python
# 添加视觉工具 app/tools/vision.py
from openai import OpenAI

def analyze_image(image_path: str, question: str = "") -> str:
    """分析图像内容"""
    client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=NVIDIA_API_KEY)
    
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode()
    
    response = client.chat.completions.create(
        model="nvidia/llama-3.2-11b-vision-instruct",  # 支持视觉的模型
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question or "Describe this image"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                ]
            }
        ]
    )
    return response.choices[0].message.content
```

**UI集成**:
```python
# main.py 添加图像上传
uploaded_image = st.file_uploader("Upload Image", type=["jpg", "png"])
if uploaded_image and prompt:
    # 先分析图像，再结合问题回答
    image_context = analyze_image(uploaded_image)
    result = run_agent(f"{prompt}\n\n[Image Context]: {image_context}")
```

---

### 2. 🎤 语音能力
**价值**: 语音输入、语音输出

**实现方案**:
```python
# 添加语音工具 app/tools/speech.py
import whisper  # OpenAI Whisper

def transcribe_audio(audio_path: str) -> str:
    """语音转文字"""
    model = whisper.load_model("base")
    result = model.transcribe(audio_path)
    return result["text"]

def text_to_speech(text: str, output_path: str = "output.mp3"):
    """文字转语音"""
    from gtts import gTTS
    tts = gTTS(text, lang='zh')
    tts.save(output_path)
    return output_path
```

**UI集成**:
```python
# main.py 添加语音按钮
if st.button("🎤 Voice Input"):
    # 录音并转文字
    audio = record_audio()
    text = transcribe_audio(audio)
    st.session_state.voice_text = text
```

---

### 3. 📊 数据分析能力
**价值**: 处理Excel、CSV，生成图表

**实现方案**:
```python
# 增强工具 app/tools/data_analyzer.py
import pandas as pd
import matplotlib.pyplot as plt

def analyze_excel(file_path: str, query: str) -> str:
    """分析Excel数据"""
    df = pd.read_excel(file_path)
    
    # AI生成pandas代码并执行
    code = generate_analysis_code(df.head(), query)
    result = execute_code_safely(code, {"df": df})
    
    return result

def create_chart(data: dict, chart_type: str) -> str:
    """生成图表"""
    plt.figure(figsize=(10, 6))
    
    if chart_type == "bar":
        plt.bar(data["labels"], data["values"])
    elif chart_type == "line":
        plt.plot(data["labels"], data["values"])
    
    plt.savefig("chart.png")
    return "chart.png"
```

---

### 4. 🌐 网页浏览能力
**价值**: 自动化网页操作

**实现方案**:
```python
# 添加浏览器工具 app/tools/browser.py
from selenium import webdriver
from selenium.webdriver.common.by import By

def browse_website(url: str, action: str, selector: str = None) -> str:
    """浏览器自动化"""
    driver = webdriver.Chrome()
    driver.get(url)
    
    if action == "screenshot":
        driver.save_screenshot("screenshot.png")
        return "screenshot.png"
    elif action == "click" and selector:
        driver.find_element(By.CSS_SELECTOR, selector).click()
    elif action == "extract":
        return driver.page_source
    
    driver.quit()
```

---

### 5. 🔗 外部API集成
**价值**: 连接外部服务

**实现方案**:
```python
# 添加API预设 app/tools/api_presets.py

API_PRESETS = {
    "weather": {
        "name": "天气查询",
        "url": "https://api.weatherapi.com/v1/current.json",
        "params": ["key", "q"],
        "description": "查询指定城市的天气"
    },
    "translate": {
        "name": "翻译服务",
        "url": "https://api.mymemory.translated.net/get",
        "params": ["q", "langpair"],
        "description": "多语言翻译"
    },
    "news": {
        "name": "新闻API",
        "url": "https://newsapi.org/v2/top-headlines",
        "params": ["apiKey", "country"],
        "description": "获取头条新闻"
    }
}

def call_preset_api(api_name: str, **kwargs) -> dict:
    """调用预设API"""
    preset = API_PRESETS.get(api_name)
    if not preset:
        return {"error": f"Unknown API: {api_name}"}
    
    response = requests.get(preset["url"], params=kwargs)
    return response.json()
```

---

## 二、智能增强

### 6. 🧠 长期记忆
**价值**: 跨会话记住用户偏好

**实现方案**:
```python
# 增强记忆 app/memory/long_term.py

class EnhancedLongTermMemory:
    def __init__(self):
        self.db_path = "data/memory/user_profile.db"
        self._init_db()
    
    def save_preference(self, key: str, value: str):
        """保存用户偏好"""
        # 例如：喜欢的编程语言、常用模型等
        
    def get_user_profile(self) -> dict:
        """获取用户画像"""
        
    def semantic_search(self, query: str) -> list:
        """语义搜索历史对话"""
```

**自动应用**:
```python
# autonomous.py 启动时加载用户画像
user_profile = memory.get_user_profile()
if user_profile.get("preferred_language") == "Python":
    context += "\n[User prefers Python for coding tasks]"
```

---

### 7. 🎯 意图识别增强
**价值**: 更准确理解用户意图

**实现方案**:
```python
# 添加意图识别 app/agents/intent_classifier.py

INTENT_TEMPLATES = {
    "code_generation": {
        "keywords": ["写代码", "实现", "编程", "generate code"],
        "follow_up": "需要什么编程语言？",
        "template": "使用{language}实现{functionality}"
    },
    "data_analysis": {
        "keywords": ["分析数据", "统计", "图表", "analyze"],
        "follow_up": "数据格式是什么？",
        "template": "分析{data_source}的{metrics}"
    },
    "web_search": {
        "keywords": ["搜索", "查找", "最新", "search"],
        "follow_up": "需要搜索什么内容？",
        "template": "搜索关于{topic}的{aspect}"
    }
}

def classify_intent(message: str) -> dict:
    """识别意图并返回模板"""
    # 使用LLM进行意图分类
    # 返回意图类型和需要的参数
```

---

### 8. 🔄 任务调度
**价值**: 定时执行、后台任务

**实现方案**:
```python
# 添加调度器 app/agents/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler

class TaskScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
    
    def schedule_task(self, task_id: str, cron_expr: str, task_func: callable):
        """定时任务"""
        self.scheduler.add_job(
            task_func,
            trigger=CronTrigger.from_crontab(cron_expr),
            id=task_id
        )
    
    def schedule_reminder(self, message: str, delay_minutes: int):
        """延迟提醒"""
        self.scheduler.add_job(
            lambda: send_notification(message),
            trigger='interval',
            minutes=delay_minutes
        )

# 使用示例
scheduler = TaskScheduler()
scheduler.schedule_task("daily_news", "0 9 * * *", fetch_daily_news)
```

---

## 三、体验增强

### 9. 💬 流式输出
**价值**: 打字机效果，实时反馈

**实现**:
```python
# main.py 使用流式输出
import streamlit as st

if prompt := st.chat_input():
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        # 调用流式API
        for chunk in chat_stream(messages, model=model):
            full_response += chunk.choices[0].delta.content
            message_placeholder.markdown(full_response + "▌")
        
        message_placeholder.markdown(full_response)
```

---

### 10. 🎨 可视化增强
**价值**: 更直观的交互

**实现方案**:
```python
# main.py 添加可视化

# 1. Agent执行流程可视化
with st.expander("🔍 Execution Details"):
    st.graphviz_chart('''
        digraph {
            User -> Router
            Router -> Researcher
            Router -> Coder
            Researcher -> LLM
            Coder -> LLM
            LLM -> Answer
        }
    ''')

# 2. 知识图谱可视化
def show_knowledge_graph(collection_name: str):
    """显示知识图谱"""
    import pyvis.network as net
    
    nodes = get_knowledge_nodes(collection_name)
    edges = get_knowledge_edges(collection_name)
    
    graph = net.Network(height="400px")
    for node in nodes:
        graph.add_node(node["id"], label=node["label"])
    for edge in edges:
        graph.add_edge(edge["source"], edge["target"])
    
    st.components.v1.html(graph.generate_html(), height=400)

# 3. 实时Token计数
token_counter = st.empty()
token_counter.metric("Tokens", current_tokens, delta=delta_tokens)
```

---

### 11. 🔔 通知系统
**价值**: 任务完成通知

**实现方案**:
```python
# app/utils/notifications.py

import smtplib
from email.mime.text import MIMEText

def send_email_notification(to: str, subject: str, body: str):
    """邮件通知"""
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["To"] = to
    
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.send_message(msg)

def send_webhook_notification(url: str, data: dict):
    """Webhook通知"""
    import requests
    requests.post(url, json=data)

def send_desktop_notification(title: str, message: str):
    """桌面通知"""
    from plyer import notification
    notification.notify(title=title, message=message)
```

---

## 四、工具增强

### 12. 🔧 更多工具

**建议添加**:

| 工具 | 用途 | 优先级 |
|------|------|--------|
| PDF解析 | 增强文档处理 | P0 |
| 图像分析 | 多模态理解 | P1 |
| 数据库操作 | CRUD数据库 | P1 |
| Git操作 | 代码版本管理 | P2 |
| 邮件发送 | 自动化通知 | P2 |
| 日历集成 | 会议安排 | P3 |

---

## 五、性能增强

### 13. ⚡ 缓存机制
```python
# app/utils/cache.py
from functools import lru_cache
import hashlib

@lru_cache(maxsize=100)
def cache_llm_response(prompt_hash: str, model: str):
    """缓存LLM响应"""
    # 相同问题不重复调用API
```

### 14. 🚀 并发执行
```python
# autonomous.py 并行调用工具
import asyncio

async def execute_tools_parallel(tools: list):
    """并行执行多个工具"""
    tasks = [execute_tool_async(t) for t in tools]
    return await asyncio.gather(*tasks)
```

---

## 实施路线图

### 第一阶段（立即）- 核心增强
1. ✅ 流式输出
2. ✅ 长期记忆启用
3. ✅ PDF解析增强

### 第二阶段（1周内）- 能力扩展
1. 图像分析
2. 数据分析
3. 更多API预设

### 第三阶段（2周内）- 体验优化
1. 语音输入/输出
2. 可视化增强
3. 通知系统

### 第四阶段（长期）- 高级功能
1. 网页自动化
2. 任务调度
3. 多语言支持

---

## 快速开始

### 最简单的增强：流式输出

只需修改 `main.py` 一处：

```python
# 找到这行：
result = run_agent(...)

# 改为：
for chunk in run_agent_stream(...):
    st.markdown(chunk)
```

---

## 建议优先级

| 增强项 | 难度 | 价值 | 建议优先级 |
|--------|------|------|-----------|
| 流式输出 | 低 | 高 | ⭐⭐⭐⭐⭐ |
| PDF增强 | 低 | 高 | ⭐⭐⭐⭐⭐ |
| 图像分析 | 中 | 高 | ⭐⭐⭐⭐ |
| 数据分析 | 中 | 高 | ⭐⭐⭐⭐ |
| 长期记忆 | 中 | 中 | ⭐⭐⭐ |
| 语音能力 | 中 | 中 | ⭐⭐⭐ |
| 网页自动化 | 高 | 中 | ⭐⭐ |
