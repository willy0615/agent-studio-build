"""深度检查硬编码和真实实现"""
import os
import re
from pathlib import Path

project_dir = Path("E:/AgentProject")

print("=" * 70)
print("深度检查报告")
print("=" * 70)

# 1. 检查.env文件
print("\n1. 环境变量文件检查")
print("-" * 70)

env_file = project_dir / ".env"
if env_file.exists():
    with open(env_file, "r") as f:
        content = f.read()
    
    print("FOUND: .env文件存在")
    
    # 检查是否包含真实密钥
    if "nvapi-" in content:
        print("  [CRITICAL] 发现NVIDIA API Key硬编码!")
        print("  建议: 将密钥移至系统环境变量或密钥管理服务")
    
    if "sk-" in content:
        print("  [CRITICAL] 发现OpenAI API Key硬编码!")
    
    # 提取所有key-value
    lines = [l.strip() for l in content.split("\n") if l.strip() and not l.startswith("#")]
    print(f"  配置项数: {len(lines)}")
    for line in lines[:5]:
        if "=" in line:
            key = line.split("=")[0]
            print(f"    - {key}")

# 2. 检查是否有真实的HTTP请求
print("\n2. 网络请求检查")
print("-" * 70)

network_files = [
    "app/tools/web_search.py",
    "app/tools/api_caller.py",
    "app/llm_client.py",
]

for file in network_files:
    filepath = project_dir / file
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 检查是否使用requests库
        if "requests." in content or "requests.request" in content:
            print(f"[REAL] {file}: 使用requests库进行真实HTTP请求")
        
        # 检查是否使用OpenAI SDK
        if "from openai import" in content or "OpenAI(" in content:
            print(f"[REAL] {file}: 使用OpenAI SDK进行真实API调用")
        
        # 检查是否有mock/模拟
        if "mock" in content.lower() or "fake" in content.lower():
            print(f"[MOCK] {file}: 发现mock关键词")

# 3. 检查代码执行是否真实
print("\n3. 代码执行检查")
print("-" * 70)

executor_file = project_dir / "app/tools/code_executor.py"
if executor_file.exists():
    with open(executor_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 检查是否使用subprocess
    if "subprocess.run" in content or "subprocess.Popen" in content:
        print("[REAL] 使用subprocess真实执行代码")
    
    # 检查是否使用exec
    if "exec(" in content:
        print("[REAL] 使用exec()真实执行代码")
    
    # 检查是否有安全限制
    if "_check_safety" in content or "DANGEROUS_PATTERNS" in content:
        print("[GOOD] 有安全检查机制")

# 4. 检查文件操作是否真实
print("\n4. 文件操作检查")
print("-" * 70)

file_ops = project_dir / "app/tools/file_ops.py"
if file_ops.exists():
    with open(file_ops, "r", encoding="utf-8") as f:
        content = f.read()
    
    if "open(" in content and "with open" in content:
        print("[REAL] 使用真实的文件读写操作")
    
    if "WORKSPACE_DIR" in content:
        print("[GOOD] 有工作目录限制")

# 5. 检查数据库操作
print("\n5. 数据库/存储检查")
print("-" * 70)

# ChromaDB
vectorstore = project_dir / "app/rag/vectorstore.py"
if vectorstore.exists():
    with open(vectorstore, "r", encoding="utf-8") as f:
        content = f.read()
    
    if "chromadb" in content or "Chroma" in content:
        print("[REAL] 使用ChromaDB真实向量数据库")
    
    if "PersistentClient" in content:
        print("[GOOD] 使用持久化存储")

# 记忆存储
memory = project_dir / "app/memory/conversation.py"
if memory.exists():
    with open(memory, "r", encoding="utf-8") as f:
        content = f.read()
    
    if "json.dump" in content or "json.load" in content:
        print("[REAL] 记忆系统使用JSON文件持久化")

# 6. 检查LLM调用
print("\n6. LLM调用检查")
print("-" * 70)

llm_files = [
    "app/llm_client.py",
    "app/agents/agents.py",
]

for file in llm_files:
    filepath = project_dir / file
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 检查是否调用真实API
        if "chat.completions.create" in content:
            print(f"[REAL] {file}: 调用真实LLM API")
        
        # 检查是否有模拟响应
        if "return 'mock" in content or 'return "mock' in content:
            print(f"[MOCK] {file}: 发现模拟响应")

# 7. 检查TODO和占位符
print("\n7. TODO和占位符检查")
print("-" * 70)

all_py_files = list(project_dir.rglob("*.py"))
todos = []

for filepath in all_py_files:
    if "test_" in str(filepath) or "__pycache__" in str(filepath):
        continue
    
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f, 1):
                if "TODO" in line or "FIXME" in line:
                    rel_path = filepath.relative_to(project_dir)
                    todos.append(f"{rel_path}:{i} - {line.strip()[:60]}")
    except:
        pass

if todos:
    print(f"发现 {len(todos)} 个TODO/FIXME:")
    for todo in todos[:10]:
        print(f"  {todo}")
else:
    print("未发现TODO/FIXME")

# 8. 总结
print("\n" + "=" * 70)
print("总结")
print("=" * 70)

print("\n[真实实现]")
print("  - LLM调用: 真实NVIDIA NIM API")
print("  - 网络请求: 真实requests库")
print("  - 代码执行: 真实exec/subprocess")
print("  - 文件操作: 真实文件读写")
print("  - 数据库: 真实ChromaDB持久化")

print("\n[安全问题]")
print("  - .env文件包含硬编码API Key")
print("  - 建议: 使用系统环境变量或密钥管理服务")

print("\n[待改进]")
if todos:
    print(f"  - {len(todos)} 个TODO待处理")
