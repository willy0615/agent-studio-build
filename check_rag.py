"""检查RAG调用链"""
import sys
sys.path.insert(0, '.')

print("=" * 70)
print("RAG KNOWLEDGE BASE CALL CHAIN ANALYSIS")
print("=" * 70)

# 1. 检查rag_retrieve在哪里被调用
print("\n1. rag_retrieve() 调用点检查")
print("-" * 70)

import os
from pathlib import Path

project_dir = Path("E:/AgentProject")
call_points = []

for root, dirs, files in os.walk(project_dir / "app"):
    dirs[:] = [d for d in dirs if d not in ["__pycache__"]]
    for f in files:
        if f.endswith(".py"):
            filepath = Path(root) / f
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as file:
                    content = file.read()
                    if "rag_retrieve" in content:
                        rel_path = filepath.relative_to(project_dir)
                        # 找到调用行
                        lines = content.split("\n")
                        for i, line in enumerate(lines):
                            if "rag_retrieve" in line and "import" not in line:
                                call_points.append((str(rel_path), i+1, line.strip()))
            except:
                pass

if call_points:
    print("Found calls:")
    for path, line, code in call_points:
        print(f"  {path}:{line}")
        print(f"    {code[:80]}...")
else:
    print("No direct calls found!")

# 2. 检查vectorstore函数调用
print("\n2. vectorstore.py 函数调用检查")
print("-" * 70)

vectorstore_funcs = [
    "add_documents",
    "query_collection", 
    "list_collections",
    "delete_collection",
    "chunk_documents",
    "get_chroma_client",
    "get_or_create_collection",
]

for func in vectorstore_funcs:
    # 搜索所有文件中的调用
    callers = []
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in ["__pycache__", ".venv"]]
        for f in files:
            if f.endswith(".py"):
                filepath = Path(root) / f
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as file:
                        content = file.read()
                        if func + "(" in content or func + " (" in content:
                            rel_path = filepath.relative_to(project_dir)
                            if "vectorstore.py" not in str(rel_path):  # 排除定义处
                                callers.append(str(rel_path))
                except:
                    pass
    
    if callers:
        print(f"{func}:")
        for c in set(callers):
            print(f"  <- {c}")
    else:
        print(f"{func}: NOT CALLED")

# 3. 检查main.py中的知识库使用
print("\n3. main.py Knowledge Base Usage")
print("-" * 70)

main_file = project_dir / "main.py"
if main_file.exists():
    with open(main_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 检查导入
    if "from app.rag" in content:
        print("Imports: FOUND")
        # 提取导入内容
        import re
        imports = re.findall(r'from app\.rag\..+ import (.+)', content)
        print(f"  Imported: {imports}")
    
    # 检查调用
    kb_calls = []
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if any(kw in line for kw in ["add_documents", "list_collections", "delete_collection", "rag_retrieve"]):
            kb_calls.append((i+1, line.strip()))
    
    if kb_calls:
        print("\nCalls in main.py:")
        for line, code in kb_calls:
            print(f"  Line {line}: {code[:70]}...")
    else:
        print("No KB function calls in main.py!")

# 4. 检查autonomous.py中的RAG使用
print("\n4. autonomous.py RAG Integration")
print("-" * 70)

auto_file = project_dir / "app/agents/autonomous.py"
if auto_file.exists():
    with open(auto_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    if "rag_retrieve" in content:
        print("rag_retrieve: INTEGRATED")
        # 找到调用位置
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "rag_retrieve" in line and "import" not in line:
                print(f"  Line {i+1}: {line.strip()[:70]}...")
    else:
        print("rag_retrieve: NOT USED")

# 5. 检查ChromaDB数据目录
print("\n5. ChromaDB Data Directory")
print("-" * 70)

chroma_dir = project_dir / "data" / "chroma"
if chroma_dir.exists():
    print(f"Directory: {chroma_dir}")
    # 统计文件
    files = list(chroma_dir.rglob("*"))
    print(f"Files: {len([f for f in files if f.is_file()])}")
    
    # 检查集合
    try:
        import sys
        sys.path.insert(0, str(project_dir))
        from app.rag.vectorstore import list_collections
        collections = list_collections()
        print(f"Collections: {collections}")
    except Exception as e:
        print(f"Error: {e}")
else:
    print("Directory: NOT EXISTS")

# 6. 测试RAG功能
print("\n6. RAG Functional Test")
print("-" * 70)

try:
    from app.rag.vectorstore import add_documents, query_collection, list_collections
    from app.rag.retriever import rag_retrieve
    
    # 列出集合
    collections = list_collections()
    print(f"Collections: {collections}")
    
    # 测试查询
    if collections:
        result = rag_retrieve("test query", collection_name=collections[0])
        print(f"Query result: {result[:100] if result else 'No results'}...")
    else:
        print("No collections - knowledge base is empty")
    
    print("[OK] RAG functions work")
except Exception as e:
    print(f"[ERROR] {e}")

print("\n" + "=" * 70)
print("ANALYSIS COMPLETE")
print("=" * 70)
