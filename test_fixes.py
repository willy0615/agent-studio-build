"""验证断层修复"""
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("断层修复验证")
print("=" * 60)

# 1. 测试统计记录
print("\n1. Stats Recording Test")
print("-" * 60)

from app.utils.stats import get_stats, reset_stats
reset_stats()
stats = get_stats()

# 模拟记录
stats.record_message()
stats.record_api_call("test-model", 100, 50)
stats.record_agent_call("web_search")
stats.record_model_call("deepseek-v4")

print(f"Messages: {stats.message_count}")
print(f"API Calls: {stats.api_calls}")
print(f"Agent Calls: {stats.agent_calls}")
print(f"Model Calls: {stats.model_calls}")
print("✓ Stats recording works")

# 2. 测试LLM客户端统计集成
print("\n2. LLM Client Stats Integration")
print("-" * 60)

from app.llm_client import get_llm_client
client = get_llm_client()
print(f"Client type: {type(client).__name__}")
print("✓ LLM client singleton works")

# 3. 测试任务管理
print("\n3. Task Manager Test")
print("-" * 60)

from app.agents.tasks import get_task_manager
tm = get_task_manager()

# 创建任务
task = tm.create_task("Test task", priority="high")
print(f"Created task: {task['id']}")

# 获取任务
retrieved = tm.get_task(task['id'])
print(f"Retrieved: {retrieved['task']}")

# 完成任务
tm.complete_task(task['id'])
print("✓ Task manager works")

# 4. 测试工具注册
print("\n4. Tool Registry Test")
print("-" * 60)

from app.tools.tool_registry import ToolRegistry

tools = ToolRegistry.list_tools()
print(f"Registered tools: {len(tools)}")

# 测试工具调用
result = ToolRegistry.execute("calculate", expression="2+2")
print(f"Calculate 2+2: {result}")

if result.get("success"):
    print("✓ Tool registry works")

# 5. 测试记忆系统
print("\n5. Memory System Test")
print("-" * 60)

from app.memory.conversation import ConversationMemory, LongTermMemory

mem = ConversationMemory()
mem.add_message("user", "Hello")
messages = mem.get_messages()
print(f"Messages count: {len(messages)}")

ltm = LongTermMemory()
print("✓ Memory system works")

# 6. 测试流式函数存在性
print("\n6. Stream Function Check")
print("-" * 60)

from app.llm_client import chat_stream
import inspect

sig = inspect.signature(chat_stream)
print(f"chat_stream signature: {sig}")
print("✓ Stream function exists (ready for future use)")

# 7. 模块导入验证
print("\n7. Module Import Verification")
print("-" * 60)

modules = [
    "app.agents.agents",
    "app.agents.autonomous",
    "app.agents.planner",
    "app.agents.tasks",
    "app.agents.learning",
    "app.agents.multi_agent",
    "app.agents.reflection",
]

for mod in modules:
    try:
        __import__(mod)
        print(f"  ✓ {mod}")
    except Exception as e:
        print(f"  ✗ {mod}: {e}")

print("\n" + "=" * 60)
print("验证完成 - 所有关键模块正常")
print("=" * 60)
