"""完整调用链分析 - 检查断层和未调用代码"""
import ast
import os
from pathlib import Path
from collections import defaultdict

project_dir = Path("E:/AgentProject")

print("=" * 70)
print("CALL CHAIN ANALYSIS - 检查断层和未调用代码")
print("=" * 70)

# 收集所有Python文件
py_files = {}
for root, dirs, files in os.walk(project_dir / "app"):
    # 跳过测试和缓存
    dirs[:] = [d for d in dirs if d not in ["__pycache__", "tests"]]
    for f in files:
        if f.endswith(".py"):
            filepath = Path(root) / f
            rel_path = filepath.relative_to(project_dir)
            py_files[str(rel_path)] = filepath

print(f"\n分析文件数: {len(py_files)}")

# 解析每个文件的函数和类
all_functions = {}  # {file: {function_name: ast_node}}
all_classes = {}    # {file: {class_name: ast_node}}
all_imports = {}    # {file: [(module, name, alias)]}

for rel_path, filepath in py_files.items():
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        all_functions[rel_path] = {}
        all_classes[rel_path] = {}
        all_imports[rel_path] = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                all_functions[rel_path][node.name] = node
            elif isinstance(node, ast.AsyncFunctionDef):
                all_functions[rel_path][node.name] = node
            elif isinstance(node, ast.ClassDef):
                all_classes[rel_path][node.name] = node
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    all_imports[rel_path].append((None, alias.name, alias.asname))
            elif isinstance(node, ast.ImportFrom):
                module = node.module
                for alias in node.names:
                    all_imports[rel_path].append((module, alias.name, alias.asname))
    except Exception as e:
        print(f"Error parsing {rel_path}: {e}")

# 分析入口点 - main.py
print("\n" + "=" * 70)
print("1. ENTRY POINT ANALYSIS - main.py")
print("=" * 70)

entry_file = "main.py"
if entry_file in all_functions:
    print(f"入口函数: {list(all_functions[entry_file].keys())}")

# 收集被调用的函数
called_functions = set()
called_methods = set()

# 从main.py开始追踪调用
def extract_calls(node):
    """提取函数调用"""
    calls = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            if isinstance(child.func, ast.Name):
                calls.append(child.func.id)
            elif isinstance(child.func, ast.Attribute):
                calls.append(child.func.attr)
    return calls

# 分析main.py的调用
main_path = project_dir / "main.py"
if main_path.exists():
    with open(main_path, "r", encoding="utf-8") as f:
        main_content = f.read()
    main_tree = ast.parse(main_content)
    
    main_calls = extract_calls(main_tree)
    called_functions.update(main_calls)
    print(f"main.py直接调用: {len(main_calls)} 个函数")
    for call in main_calls[:20]:
        print(f"  - {call}")

# 分析所有文件的调用
print("\n" + "=" * 70)
print("2. ALL FUNCTION CALLS")
print("=" * 70)

for rel_path, filepath in py_files.items():
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        tree = ast.parse(content)
        calls = extract_calls(tree)
        called_functions.update(calls)
    except:
        pass

print(f"总调用函数数: {len(called_functions)}")

# 分析定义的函数
print("\n" + "=" * 70)
print("3. DEFINED FUNCTIONS")
print("=" * 70)

all_defined = set()
for rel_path, funcs in all_functions.items():
    for func_name in funcs:
        all_defined.add(func_name)

print(f"总定义函数数: {len(all_defined)}")

# 找出未被调用的函数
print("\n" + "=" * 70)
print("4. POTENTIALLY UNCALLED FUNCTIONS")
print("=" * 70)

# 排除特殊函数
exclude_patterns = [
    "__init__", "__str__", "__repr__", "__call__", "__len__",
    "__getitem__", "__setitem__", "__delitem__", "__iter__",
    "__enter__", "__exit__", "__bool__",
    "main", "app",  # 入口点
]

uncalled = []
for rel_path, funcs in all_functions.items():
    for func_name in funcs:
        # 跳过特殊函数
        if any(pattern in func_name for pattern in exclude_patterns):
            continue
        
        # 跳过私有函数（可能是内部使用）
        if func_name.startswith("_") and not func_name.startswith("__"):
            continue
        
        # 检查是否被调用
        if func_name not in called_functions:
            uncalled.append((rel_path, func_name))

if uncalled:
    print(f"\n发现 {len(uncalled)} 个可能未被调用的函数:")
    for file, func in uncalled:
        print(f"  {file}::{func}")
else:
    print("所有函数都被调用")

# 分析模块导入关系
print("\n" + "=" * 70)
print("5. MODULE IMPORT ANALYSIS")
print("=" * 70)

# 检查哪些模块被导入
imported_modules = set()
for rel_path, imports in all_imports.items():
    for module, name, alias in imports:
        if module and module.startswith("app"):
            imported_modules.add(module)
        if name and isinstance(name, str) and name.startswith("app"):
            imported_modules.add(name)

print(f"被导入的app模块数: {len(imported_modules)}")
for mod in sorted(imported_modules):
    print(f"  - {mod}")

# 检查工具注册情况
print("\n" + "=" * 70)
print("6. TOOL REGISTRY ANALYSIS")
print("=" * 70)

tool_registry = project_dir / "app/tools/tool_registry.py"
if tool_registry.exists():
    with open(tool_registry, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 提取注册的工具
    import re
    registered = re.findall(r'"(\w+)":\s*\{[^}]*"module":\s*"([^"]+)"', content)
    
    print(f"已注册工具: {len(registered)}")
    for tool_name, module in registered:
        print(f"  - {tool_name} -> {module}")
    
    # 检查模块是否存在
    print("\n检查工具模块是否存在:")
    for tool_name, module in registered:
        module_path = project_dir / module.replace(".", "/") + ".py"
        exists = "OK" if module_path.exists() else "MISSING"
        print(f"  {tool_name}: {exists}")

# 检查Agent调用链
print("\n" + "=" * 70)
print("7. AGENT INTEGRATION CHECK")
print("=" * 70)

agent_modules = [
    "app/agents/agents.py",
    "app/agents/autonomous.py",
    "app/agents/react_agent.py",
    "app/agents/planner.py",
    "app/agents/reflection.py",
    "app/agents/multi_agent.py",
    "app/agents/learning.py",
    "app/agents/tasks.py",
]

for module in agent_modules:
    filepath = project_dir / module
    if filepath.exists():
        # 检查是否在main.py中被导入
        module_import = module.replace("/", ".").replace(".py", "")
        if module_import.replace("app.", "") in str(all_imports.get("main.py", [])):
            status = "IMPORTED"
        else:
            # 检查是否被其他已导入模块使用
            imported_somewhere = False
            for rel_path, imports in all_imports.items():
                for mod, name, alias in imports:
                    if name and module_import in str(name):
                        imported_somewhere = True
                        break
            status = "INDIRECT" if imported_somewhere else "NOT IMPORTED"
        
        print(f"  {module}: {status}")

# 检查RAG模块
print("\n" + "=" * 70)
print("8. RAG MODULE CHECK")
print("=" * 70)

rag_modules = [
    "app/rag/vectorstore.py",
    "app/rag/retriever.py",
]

for module in rag_modules:
    filepath = project_dir / module
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 检查是否定义了关键函数
        has_add = "add_documents" in content or "add_texts" in content
        has_search = "search" in content or "query" in content or "retrieve" in content
        
        print(f"  {module}:")
        print(f"    添加文档: {'YES' if has_add else 'NO'}")
        print(f"    搜索功能: {'YES' if has_search else 'NO'}")

# 检查记忆模块
print("\n" + "=" * 70)
print("9. MEMORY MODULE CHECK")
print("=" * 70)

memory_file = project_dir / "app/memory/conversation.py"
if memory_file.exists():
    with open(memory_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 检查关键方法
    methods = ["add_message", "get_messages", "compress_memory", "save", "load"]
    print("  ConversationMemory methods:")
    for method in methods:
        has_method = f"def {method}" in content
        print(f"    {method}: {'YES' if has_method else 'NO'}")

print("\n" + "=" * 70)
print("ANALYSIS COMPLETE")
print("=" * 70)
