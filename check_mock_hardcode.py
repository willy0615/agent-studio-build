"""检查模拟代码和硬编码"""
import os
import re
from pathlib import Path

project_dir = Path("E:/AgentProject")

print("=" * 60)
print("检查模拟代码和硬编码")
print("=" * 60)

# 要检查的文件
files_to_check = []
for root, dirs, files in os.walk(project_dir / "app"):
    for f in files:
        if f.endswith(".py"):
            files_to_check.append(Path(root) / f)

print(f"\n检查文件数: {len(files_to_check)}")

# 模拟关键词
mock_keywords = [
    "mock", "fake", "dummy", "stub", "TODO", "FIXME",
    "placeholder", "example.com", "test@test.com",
    "hardcoded", "临时", "测试", "示例",
]

# 硬编码模式
hardcoded_patterns = [
    (r'api_key\s*=\s*["\'][^"\']{20,}["\']', "API Key"),
    (r'password\s*=\s*["\'][^"\']+["\']', "Password"),
    (r'secret\s*=\s*["\'][^"\']+["\']', "Secret"),
    (r'token\s*=\s*["\'][^"\']{20,}["\']', "Token"),
    (r'https?://(?!localhost|127\.0\.0\.1|example\.org)["\']', "URL"),
]

issues = []

for filepath in files_to_check:
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            lines = content.split("\n")
            
            # 检查模拟关键词
            for i, line in enumerate(lines, 1):
                for keyword in mock_keywords:
                    if keyword.lower() in line.lower():
                        # 排除注释中的TODO/FIXME
                        if keyword in ["TODO", "FIXME"] and line.strip().startswith("#"):
                            continue
                        # 排除测试文件
                        if "test_" in str(filepath):
                            continue
                        issues.append({
                            "file": str(filepath.relative_to(project_dir)),
                            "line": i,
                            "type": "Mock Keyword",
                            "content": line.strip()[:80],
                            "keyword": keyword,
                        })
            
            # 检查硬编码模式
            for pattern, name in hardcoded_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    # 跳过环境变量引用
                    matched_text = match.group(0)
                    if "os.environ" in matched_text or "getenv" in matched_text:
                        continue
                    # 找到行号
                    line_num = content[:match.start()].count("\n") + 1
                    issues.append({
                        "file": str(filepath.relative_to(project_dir)),
                        "line": line_num,
                        "type": f"Hardcoded {name}",
                        "content": matched_text[:80],
                    })
    
    except Exception as e:
        print(f"Error reading {filepath}: {e}")

# 按文件分组
issues_by_file = {}
for issue in issues:
    file = issue["file"]
    if file not in issues_by_file:
        issues_by_file[file] = []
    issues_by_file[file].append(issue)

# 输出结果
print("\n" + "=" * 60)
print(f"发现 {len(issues)} 个潜在问题")
print("=" * 60)

if issues_by_file:
    for file, file_issues in issues_by_file.items():
        print(f"\n文件: {file}")
        for issue in file_issues:
            print(f"  行 {issue['line']}: [{issue['type']}]")
            print(f"    {issue['content']}")
else:
    print("\n未发现明显的模拟代码或硬编码问题")

# 特别检查关键文件
print("\n" + "=" * 60)
print("关键文件详细检查")
print("=" * 60)

key_files = [
    "app/llm_client.py",
    "app/config.py",
    "app/tools/web_search.py",
    "app/tools/api_caller.py",
]

for file in key_files:
    filepath = project_dir / file
    if filepath.exists():
        print(f"\n--- {file} ---")
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
        # 检查是否使用环境变量
        if "os.environ" in content or "getenv" in content:
            print("  [OK] 使用环境变量")
        else:
            print("  [WARN] 未检测到环境变量使用")
        
        # 检查是否有硬编码URL
        urls = re.findall(r'https?://[^\s"\']+', content)
        if urls:
            print(f"  [URL] 发现 {len(urls)} 个URL")
            for url in urls[:3]:
                if "localhost" not in url and "127.0.0.1" not in url:
                    print(f"    - {url}")
        
        # 检查是否有硬编码密钥
        if 'api_key' in content.lower() or 'apikey' in content.lower():
            if 'os.environ' in content or 'getenv' in content:
                print("  [OK] API Key从环境变量读取")
            else:
                print("  [WARN] API Key可能硬编码")
        
        # 检查是否是真实实现
        if "def " in content:
            funcs = re.findall(r'def (\w+)\(', content)
            print(f"  [Functions] {len(funcs)} 个函数")
            
            # 检查是否有pass或...占位符
            if content.count("pass") > len(funcs) * 0.3:
                print("  [WARN] 大量pass语句，可能是占位实现")
            
            if "..." in content and "def " in content:
                print("  [WARN] 发现...占位符")

print("\n" + "=" * 60)
print("检查完成")
print("=" * 60)
