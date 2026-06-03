#!/usr/bin/env python3
"""
修改桌面应用：连接远程后端 API
后端地址: http://64.90.1.179:8501
"""

import sys
from pathlib import Path

# 读取原文件
main_py = Path("E:/AgentProject/desktop_app/main.py")
content = main_py.read_text(encoding="utf-8")

print(f"原文件大小: {len(content)} 字节")

# 方案：修改 AgentWorker，使用 requests 调用后端 API
# Streamlit 默认没有 REST API，所以我们需要：
# 1. 在后端的 app/ 中添加 FastAPI 接口
# 2. 或者让桌面端直接调用 NVIDIA API

# 这里选择方案2：桌面端直接调用 NVIDIA API（独立运行）
# 修改 AgentWorker 类

new_agent_worker = '''# ============================================================
# Agent工作线程 - 直接调用 NVIDIA API
# ============================================================
class AgentWorker(QThread):
    result_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    progress_update = pyqtSignal(str)
    
    def __init__(self, task, model="deepseek-ai/deepseek-v4-flash", mode="auto", context="", history=None):
        super().__init__()
        self.task = task
        self.model = model
        self.mode = mode
        self.context = context
        self.history = history or []
    
    def run(self):
        import time
        import os
        from pathlib import Path
        
        start_time = time.time()
        
        try:
            # 读取配置
            from dotenv import load_dotenv
            load_dotenv()
            
            api_key = os.getenv("NVIDIA_API_KEY", "")
            base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
            
            if not api_key:
                # 尝试从设置文件读取
                settings_file = Path.home() / ".agent_studio" / "settings.env"
                if settings_file.exists():
                    load_dotenv(settings_file)
                    api_key = os.getenv("NVIDIA_API_KEY", "")
                    base_url = os.getenv("NVIDIA_BASE_URL", base_url)
            
            if not api_key:
                self.error_occurred.emit("API Key 未配置，请在设置页面配置 NVIDIA_API_KEY")
                return
            
            self.progress_update.emit("正在连接 NVIDIA API...")
            
            # 使用 OpenAI SDK
            try:
                from openai import OpenAI
            except ImportError:
                self.error_occurred.emit("openai 库未安装，请运行: pip install openai")
                return
            
            client = OpenAI(api_key=api_key, base_url=base_url)
            
            # 构建消息历史
            messages = []
            for msg in self.history:
                if msg.get("role") in ["user", "assistant"]:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            # 添加当前任务
            if self.context:
                messages.append({
                    "role": "system",
                    "content": f"上下文: {self.context}"
                })
            
            messages.append({"role": "user", "content": self.task})
            
            self.progress_update.emit(f"正在调用模型: {self.model}...")
            
            # 调用 API
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
                stream=False
            )
            
            elapsed = int((time.time() - start_time) * 1000)
            answer = response.choices[0].message.content
            
            result = {
                "success": True,
                "answer": answer,
                "mode": self.mode,
                "time_ms": elapsed,
                "tool_calls": [],
                "backend_connected": True,
                "model": self.model
            }
            
            self.progress_update.emit(f"完成 ({elapsed}ms)")
            self.result_ready.emit(result)
            
        except Exception as e:
            import traceback
            elapsed = int((time.time() - start_time) * 1000)
            error_msg = f"调用失败: {str(e)}\\n\\n"
            self.error_occurred.emit(error_msg)
'''

# 找到旧 AgentWorker 类并替换
import re

# 定位 AgentWorker 类的开始和结束
pattern = r'# =+\\n# Agent工作线程[\\s\\S]*?def run\(self\):[\\s\\S]*?self\\.result_ready\\.emit\\(result\\)\\s*\\n\\s*else:'  

# 更简单的方法：直接替换整个类
start_marker = '# ============================================================\n# Agent工作线程'
end_marker = '                self.result_ready.emit(result)'

if start_marker in content:
    # 找到类的结束位置
    start_idx = content.find(start_marker)
    
    # 找到类的结束（下一个类或函数定义）
    next_class = content.find('# =+', start_idx + 100)
    
    if next_class > start_idx:
        # 替换
        content_new = content[:start_idx] + new_agent_worker + '\\n' + content[next_class:]
        
        # 保存
        output_file = Path("E:/AgentProject/desktop_app/main_api.py")
        output_file.write_text(content_new, encoding="utf-8")
        
        print(f"[OK] 已生成新文件: {output_file}")
        print(f"新文件大小: {len(content_new)} 字节")
    else:
        print("[ERROR] 找不到类的结束位置")
else:
    print("[ERROR] 找不到 AgentWorker 类")

print("\\n完成！")
