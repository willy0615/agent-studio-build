#!/usr/bin/env python3
"""
Agent Studio - Tkinter 简化版（确保能编译成 EXE）
功能：聊天（调用远程服务器 API）
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import requests
import json
import threading
import time
from pathlib import Path
from dotenv import load_dotenv
import os

# 读取配置
load_dotenv()
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")

# 远程服务器 API
API_SERVER = "http://64.90.1.179:8000"


class AgentStudioApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Agent Studio - 智能体工作室")
        self.root.geometry("1000x700")
        
        self.chat_history = []
        self.setup_ui()
    
    def setup_ui(self):
        """创建界面"""
        # 顶部工具栏
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(toolbar, text="模型:").pack(side="left", padx=5)
        self.model_var = tk.StringVar(value="deepseek-ai/deepseek-v4-flash")
        model_combo = ttk.Combobox(toolbar, textvariable=self.model_var, width=30)
        model_combo["values"] = [
            "deepseek-ai/deepseek-v4-flash",
            "deepseek-ai/deepseek-v4-pro",
            "z-ai/glm-5.1"
        ]
        model_combo.pack(side="left", padx=5)
        
        ttk.Label(toolbar, text="模式:").pack(side="left", padx=5)
        self.mode_var = tk.StringVar(value="auto")
        mode_combo = ttk.Combobox(toolbar, textvariable=self.mode_var, width=15)
        mode_combo["values"] = ["auto", "simple", "react", "multi"]
        mode_combo.pack(side="left", padx=5)
        
        # 聊天区域
        self.chat_area = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            font=("Microsoft YaHei", 10),
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="white"
        )
        self.chat_area.pack(fill="both", expand=True, padx=5, pady=5)
        self.chat_area.config(state="disabled")
        
        # 底部输入区域
        input_frame = ttk.Frame(self.root)
        input_frame.pack(fill="x", padx=5, pady=5)
        
        self.input_text = scrolledtext.ScrolledText(
            input_frame,
            height=3,
            font=("Microsoft YaHei", 10)
        )
        self.input_text.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.input_text.bind("<Control-Return>", self.send_message)
        
        send_btn = ttk.Button(input_frame, text="发送", command=self.send_message)
        send_btn.pack(side="right")
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief="sunken", anchor="w")
        status_bar.pack(fill="x", side="bottom")
    
    def add_message(self, text, is_user=True):
        """添加消息到聊天区域"""
        self.chat_area.config(state="normal")
        
        tag = "user" if is_user else "assistant"
        prefix = "我: " if is_user else "智能体: "
        
        self.chat_area.insert(tk.END, prefix + text + "\n\n", tag)
        
        # 配置标签样式
        self.chat_area.tag_config("user", foreground="#569cd6")
        self.chat_area.tag_config("assistant", foreground="#4ec9b0")
        
        self.chat_area.config(state="disabled")
        self.chat_area.see(tk.END)
    
    def send_message(self, event=None):
        """发送消息"""
        message = self.input_text.get("1.0", tk.END).strip()
        if not message:
            return
        
        self.input_text.delete("1.0", tk.END)
        self.add_message(message, is_user=True)
        self.chat_history.append({"role": "user", "content": message})
        
        # 在新线程中调用 API
        thread = threading.Thread(target=self.call_api, args=(message,))
        thread.daemon = True
        thread.start()
    
    def call_api(self):
        """调用远程服务器 API"""
        message = self.chat_history[-1]["content"]
        model = self.model_var.get()
        mode = self.mode_var.get()
        
        self.status_var.set("正在连接远程服务器...")
        
        try:
            # 优先调用远程服务器
            payload = {
                "message": message,
                "model": model,
                "mode": mode,
                "history": self.chat_history[:-1]
            }
            
            response = requests.post(
                f"{API_SERVER}/api/chat",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get("answer", "")
                elapsed = data.get("time_ms", 0)
                
                self.chat_history.append({"role": "assistant", "content": answer})
                self.add_message(f"{answer}\n\n[模式: {mode}, 耗时: {elapsed}ms]", is_user=False)
                self.status_var.set(f"完成 ({elapsed}ms)")
                return
            else:
                self.status_var.set("服务器错误，降级到本地 API...")
        
        except Exception as e:
            self.status_var.set(f"无法连接服务器: {e}，降级到本地 API...")
        
        # 降级到 NVIDIA API
        self.call_nvidia_api(message, model, mode)
    
    def call_nvidia_api(self, message, model, mode):
        """降级调用 NVIDIA API"""
        if not NVIDIA_API_KEY:
            self.add_message("错误: API Key 未配置，请在 .env 文件中配置 NVIDIA_API_KEY", is_user=False)
            self.status_var.set("错误: API Key 未配置")
            return
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=NVIDIA_API_KEY, base_url=NVIDIA_BASE_URL)
            
            messages = [{"role": m["role"], "content": m["content"]} for m in self.chat_history]
            
            self.status_var.set(f"正在调用模型: {model}...")
            
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            
            answer = response.choices[0].message.content
            
            self.chat_history.append({"role": "assistant", "content": answer})
            self.add_message(answer, is_user=False)
            self.status_var.set("完成（本地 API）")
        
        except Exception as e:
            self.add_message(f"错误: {str(e)}", is_user=False)
            self.status_var.set("错误")


def main():
    root = tk.Tk()
    app = AgentStudioApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
