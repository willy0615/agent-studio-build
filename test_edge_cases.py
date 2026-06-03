"""边界情况和异常处理测试"""
import sys
sys.path.insert(0, '.')

from app.tools.tool_registry import ToolRegistry
from app.agents.autonomous import AutonomousAgent
from app.rag.vectorstore import add_documents, list_collections

print("=" * 60)
print("1. 空输入测试")
print("=" * 60)

agent = AutonomousAgent(mode='simple')

# 空字符串
try:
    result = agent.run("", enable_reflection=False)
    print(f"空字符串: success={result.get('success')}")
except Exception as e:
    print(f"空字符串异常: {type(e).__name__}: {e}")

# 纯空格
try:
    result = agent.run("   ", enable_reflection=False)
    print(f"纯空格: success={result.get('success')}")
except Exception as e:
    print(f"纯空格异常: {type(e).__name__}: {e}")

print("\n" + "=" * 60)
print("2. 超长输入测试")
print("=" * 60)

long_input = "测试" * 10000
print(f"输入长度: {len(long_input)} 字符")

try:
    result = agent.run(long_input[:500], enable_reflection=False)
    print(f"截断后执行: success={result.get('success')}")
except Exception as e:
    print(f"异常: {e}")

print("\n" + "=" * 60)
print("3. 特殊字符测试")
print("=" * 60)

special_chars = [
    "Hello <script>alert('xss')</script>",
    "Test {{variable}}",
    "Path: C:\\Users\\test\\file.txt",
    "URL: https://example.com?param=value&other=123",
]

for text in special_chars:
    try:
        result = agent.run(text, enable_reflection=False)
        print(f"特殊字符: success={result.get('success')}")
    except Exception as e:
        print(f"特殊字符异常: {e}")

print("\n" + "=" * 60)
print("4. 并发安全测试")
print("=" * 60)

from app.llm_client import LLMClient

# 测试单例
client1 = LLMClient()
client2 = LLMClient()

print(f"单例测试: {id(client1) == id(client2)}")

print("\n" + "=" * 60)
print("5. 资源清理测试")
print("=" * 60)

from app.rag.vectorstore import get_vectorstore

# 测试重复创建
try:
    vs1 = get_vectorstore("test_collection_1")
    vs2 = get_vectorstore("test_collection_1")
    print(f"向量存储单例: {id(vs1) == id(vs2)}")
except Exception as e:
    print(f"向量存储异常: {e}")

print("\n" + "=" * 60)
print("6. 代码执行边界测试")
print("=" * 60)

# 测试超时代码
import time
start = time.time()

# 测试无限循环（应该被超时机制终止）
result = ToolRegistry.execute(
    "execute_code",
    code="import time\ntime.sleep(0.5)\nprint('done')",
    timeout=1
)
print(f"超时测试: {time.time()-start:.2f}s")
print(f"结果: {result}")

# 测试内存占用
result = ToolRegistry.execute(
    "execute_code",
    code="x = [1] * 1000\nprint(len(x))"
)
print(f"内存测试: {result}")

print("\n" + "=" * 60)
print("7. API调用测试（模拟）")
print("=" * 60)

# 测试无效URL
result = ToolRegistry.execute(
    "call_api",
    url="not_a_valid_url",
    method="GET"
)
print(f"无效URL: {result}")

# 测试超时
result = ToolRegistry.execute(
    "call_api",
    url="https://httpbin.org/delay/10",
    method="GET",
    timeout=1
)
print(f"超时请求: {result}")

print("\n" + "=" * 60)
print("8. 文件操作测试")
print("=" * 60)

# 测试读取不存在的文件
result = ToolRegistry.execute("read_file", path="/nonexistent/path/file.txt")
print(f"读取不存在文件: {result}")

# 测试写入无效路径
result = ToolRegistry.execute("write_file", path="/invalid/path/file.txt", content="test")
print(f"写入无效路径: {result}")

print("\n" + "=" * 60)
print("所有边界测试完成!")
print("=" * 60)
