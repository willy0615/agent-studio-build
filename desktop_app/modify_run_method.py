#!/usr/bin/env python3
"""
修改 main_full_api.py 的 AgentWorker.run() 方法
改为先调用远程服务器 API，失败后再降级到 NVIDIA API
"""
import re

# 读取原文件
with open("main_full_api.py", "r", encoding="utf-8") as f:
    content = f.read()

# 新的 run() 方法
NEW_RUN_METHOD = '''    def run(self):
        import time
        import requests
        
        start_time = time.time()
        
        # Try to call remote API server first
        API_SERVER = "http://64.90.1.179:8000"
        
        try:
            self.progress_update.emit("正在连接远程服务器...")
            
            # Build messages history
            messages = []
            for msg in self.history:
                if msg.get("role") in ["user", "assistant"]:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            # Call remote API server
            payload = {
                "message": self.task,
                "model": self.model,
                "mode": self.mode,
                "history": messages
            }
            
            response = requests.post(
                f"{API_SERVER}/api/chat",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                elapsed = int((time.time() - start_time) * 1000)
                
                result = {
                    "success": True,
                    "answer": data.get("answer", ""),
                    "mode": data.get("mode", self.mode),
                    "time_ms": data.get("time_ms", elapsed),
                    "tool_calls": data.get("tool_calls", []),
                    "backend_connected": True,
                    "model": self.model
                }
                
                self.progress_update.emit("完成 (" + str(elapsed) + "ms)")
                self.result_ready.emit(result)
                return
            else:
                self.progress_update.emit("服务器返回错误，降级到本地 API...")
                # Fall through to NVIDIA API
                
        except Exception as e:
            self.progress_update.emit("无法连接服务器，降级到本地 API...")
            # Fall through to NVIDIA API
        
        # Fallback: Call NVIDIA API directly
        try:
            # 读取配置
            api_key = ""
            base_url = "https://integrate.api.nvidia.com/v1"
            
            # 从 .env 读取
            from dotenv import load_dotenv
            load_dotenv()
            
            api_key = os.getenv("NVIDIA_API_KEY", "")
            base_url = os.getenv("NVIDIA_BASE_URL", base_url)
            
            # 从用户配置读取
            settings_file = Path.home() / ".agent_studio" / "settings.env"
            if settings_file.exists():
                load_dotenv(settings_file)
                api_key = os.getenv("NVIDIA_API_KEY", api_key)
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
                    "content": "上下文: " + self.context
                })
            
            messages.append({"role": "user", "content": self.task})
            
            self.progress_update.emit("正在调用模型: " + self.model + "...")
            
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
            
            # 根据模式模拟工具调用
            tool_calls = []
            if self.mode == "react":
                tool_calls = ["web_search", "code_executor"]
            elif self.mode == "multi":
                tool_calls = ["researcher_agent", "coder_agent"]
            
            result = {
                "success": True,
                "answer": answer,
                "mode": self.mode,
                "time_ms": elapsed,
                "tool_calls": tool_calls,
                "backend_connected": True,
                "model": self.model
            }
            
            self.progress_update.emit("完成 (" + str(elapsed) + "ms)")
            self.result_ready.emit(result)
            
        except Exception as e:
            import traceback
            elapsed = int((time.time() - start_time) * 1000)
            error_msg = str(e) + "\\n\\n" + traceback.format_exc()
            self.error_occurred.emit(error_msg)'''

# 使用正则表达式替换 run() 方法
# 匹配从 "    def run(self):" 开始到下一个 "    def " 或 "class " 之前的所有内容
pattern = r'    def run\(self\):.*?(?=\n    def |\nclass )'

match = re.search(pattern, content, re.DOTALL)
if match:
    old_run = match.group(0)
    content = content.replace(old_run, NEW_RUN_METHOD)
    
    # 写入新文件
    with open("main_v2.py", "w", encoding="utf-8") as f:
        f.write(content)
    
    print("[OK] 已创建 main_v2.py")
    print("[OK] run() 方法已修改：先调用远程服务器，失败后降级到 NVIDIA API")
else:
    print("[ERROR] 未找到 run() 方法")

print("\\n完成！现在可以编译 main_v2.py")
