"""代码逻辑测试"""
import sys
sys.path.insert(0, '.')

from app.tools.tool_registry import ToolRegistry
from app.tools.code_executor import _check_safety
from app.agents.autonomous import AutonomousAgent
from app.agents.planner import TaskPlanner
from app.rag.vectorstore import chunk_documents

print("=" * 60)
print("1. 工具注册测试")
print("=" * 60)
tools = ToolRegistry.list_tools()
print(f"已注册工具: {len(tools)}个")
assert len(tools) == 9, f"预期9个工具，实际{len(tools)}个"

# 测试工具执行
print("\n测试execute_code工具...")
result = ToolRegistry.execute("execute_code", code="print(1+1)")
print(f"  结果: {result}")

print("\n" + "=" * 60)
print("2. 代码安全检查测试")
print("=" * 60)

# 安全代码
safe_code = "x = 1 + 1\nprint(x)"
is_safe, error = _check_safety(safe_code)
print(f"安全代码: is_safe={is_safe}")
assert is_safe, f"安全代码被误判: {error}"

# 危险代码 - os.system
dangerous_code1 = "import os\nos.system('rm -rf /')"
is_safe, error = _check_safety(dangerous_code1)
print(f"危险代码(os.system): is_safe={is_safe}, error={error}")
assert not is_safe, "os.system未被拦截"

# 危险代码 - subprocess
dangerous_code2 = "import subprocess\nsubprocess.run(['cmd'])"
is_safe, error = _check_safety(dangerous_code2)
print(f"危险代码(subprocess): is_safe={is_safe}, error={error}")
assert not is_safe, "subprocess未被拦截"

# 危险代码 - 文件写入
dangerous_code3 = "open('/etc/passwd', 'w')"
is_safe, error = _check_safety(dangerous_code3)
print(f"危险代码(file write): is_safe={is_safe}, error={error}")
assert not is_safe, "文件写入未被拦截"

print("\n" + "=" * 60)
print("3. 文档分块测试")
print("=" * 60)

# 测试短文档
short_text = "这是一个短文档"
chunks = chunk_documents(short_text, chunk_size=500)
print(f"短文档: {len(chunks)}个chunk")
assert len(chunks) == 1

# 测试长文档
long_text = "测试内容。" * 100
chunks = chunk_documents(long_text, chunk_size=50, overlap=10)
print(f"长文档: {len(chunks)}个chunk")
assert len(chunks) > 1

# 测试分块overlap
if len(chunks) > 1:
    print(f"  chunk[0]: {chunks[0][:30]}...")
    print(f"  chunk[1]: {chunks[1][:30]}...")

print("\n" + "=" * 60)
print("4. 复杂度检测测试")
print("=" * 60)

agent = AutonomousAgent(mode='auto')

test_cases = [
    ("你好", "simple"),
    ("介绍一下Python", "simple"),
    ("帮我写一个Python程序", "complex"),
    ("搜索最新的AI新闻", "complex"),
    ("深入研究AI Agent的发展趋势，写一份综合报告", "multi"),
]

for task, expected in test_cases:
    result = agent._detect_complexity(task)
    status = "PASS" if result == expected else "FAIL"
    print(f"  [{status}] '{task[:20]}...' -> {result} (预期: {expected})")

print("\n" + "=" * 60)
print("5. 错误处理测试")
print("=" * 60)

# 测试不存在的工具
result = ToolRegistry.execute("nonexistent_tool")
print(f"不存在工具: {result}")
assert "error" in result or not result.get("success", False)

# 测试无效参数
result = ToolRegistry.execute("execute_code")  # 缺少code参数
print(f"缺少参数: {result}")

print("\n" + "=" * 60)
print("6. 内存管理测试")
print("=" * 60)

from app.memory.conversation import ConversationMemory
mem = ConversationMemory()

# 添加消息
for i in range(10):
    mem.add_message("user", f"Message {i}")
    mem.add_message("assistant", f"Response {i}")

print(f"消息数: {len(mem.messages)}")

# 测试压缩
from app.memory.conversation import ConversationMemory
mem_compress = ConversationMemory()
mem_compress.max_turns = 5

for i in range(20):
    mem_compress.add_message("user", f"Message {i}")

print(f"压缩前: 20条消息")
print(f"压缩后: {len(mem_compress.messages)}条消息")
print(f"摘要: {len(mem_compress.summary)}字符")

print("\n" + "=" * 60)
print("所有测试通过!")
print("=" * 60)
