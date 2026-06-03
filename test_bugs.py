"""代码逻辑BUG检查（跳过RAG）"""
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("1. 检查llm_client单例模式")
print("=" * 60)

from app.llm_client import LLMClient

# 测试单例
client1 = LLMClient()
client2 = LLMClient()
print(f"单例验证: {id(client1) == id(client2)}")

# 检查是否有连接池
print(f"客户端类型: {type(client1.client)}")
print(f"是否有连接池: {hasattr(client1.client, '_client')}")

print("\n" + "=" * 60)
print("2. 检查代码执行沙箱")
print("=" * 60)

from app.tools.code_executor import execute_code, _check_safety

# 测试沙箱隔离
result = execute_code("import os\nprint(os.getcwd())")
print(f"沙箱测试(os模块): {result}")

result = execute_code("__import__('subprocess').run(['echo', 'test'])")
print(f"沙箱测试(subprocess): {result}")

# 测试资源限制
import time
start = time.time()
result = execute_code("for i in range(1000000): pass\nprint('done')")
print(f"循环执行: {time.time()-start:.2f}s")
print(f"结果: {result}")

print("\n" + "=" * 60)
print("3. 检查记忆压缩逻辑")
print("=" * 60)

from app.memory.conversation import ConversationMemory

mem = ConversationMemory()
mem.max_turns = 5

# 添加超过阈值的消息
for i in range(20):
    mem.add_message("user", f"User message {i}" * 10)
    mem.add_message("assistant", f"Assistant response {i}" * 10)

print(f"添加消息数: 40")
print(f"压缩后消息数: {len(mem.messages)}")
print(f"是否有摘要: {len(mem.summary) > 0}")
print(f"摘要长度: {len(mem.summary)}")

# 验证不会无限增长
assert len(mem.messages) <= mem.max_turns * 2, "记忆未正确压缩"

print("\n" + "=" * 60)
print("4. 检查任务规划逻辑")
print("=" * 60)

from app.agents.planner import TaskPlanner

planner = TaskPlanner()

# 测试空任务
try:
    result = planner.plan("")
    print(f"空任务处理: {result}")
except Exception as e:
    print(f"空任务异常: {type(e).__name__}")

# 测试简单任务
result = planner.plan("计算1+1")
print(f"简单任务: {result}")

print("\n" + "=" * 60)
print("5. 检查错误重试逻辑")
print("=" * 60)

from app.llm_client import LLMClient

client = LLMClient()

# 测试无效模型
try:
    result = client.chat("invalid_model", "test")
    print(f"无效模型: {result}")
except Exception as e:
    print(f"无效模型异常: {type(e).__name__}")

# 测试空消息
try:
    result = client.chat("deepseek-ai/deepseek-v4-flash", "")
    print(f"空消息: {result}")
except Exception as e:
    print(f"空消息异常: {type(e).__name__}")

print("\n" + "=" * 60)
print("6. 检查多Agent协作逻辑")
print("=" * 60)

from app.agents.multi_agent import MultiAgentOrchestrator

orchestrator = MultiAgentOrchestrator()

# 检查Agent注册
print(f"已注册Agent: {list(orchestrator.agents.keys())}")

# 检查工作流
print(f"工作流步骤: {orchestrator.workflow}")

print("\n" + "=" * 60)
print("7. 检查学习模块持久化")
print("=" * 60)

from app.agents.learning import get_skill_learner
import os

learner = get_skill_learner()

# 检查数据目录
data_dir = "E:\\AgentProject\\data\\skills"
print(f"数据目录存在: {os.path.exists(data_dir)}")

# 测试记录反馈
learner.record_feedback("test task", "test response", "positive")
stats = learner.get_stats()
print(f"反馈统计: {stats}")

# 测试模式提取
learner.extract_patterns()
print(f"学习统计: {learner.get_stats()}")

print("\n" + "=" * 60)
print("8. 检查工具注册完整性")
print("=" * 60)

from app.tools.tool_registry import ToolRegistry

tools = ToolRegistry.list_tools()
print(f"注册工具数: {len(tools)}")

# 验证每个工具都有必需字段
for tool in tools:
    assert "name" in tool, f"工具缺少name字段"
    assert "description" in tool, f"工具{tool.get('name')}缺少description"
    assert "parameters" in tool, f"工具{tool.get('name')}缺少parameters"
    print(f"  ✓ {tool['name']}: {tool['description'][:30]}...")

print("\n" + "=" * 60)
print("所有逻辑检查完成!")
print("=" * 60)
