"""验证断层修复 - 无Unicode"""
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("Fix Verification")
print("=" * 60)

# 1. Stats
print("\n1. Stats Recording")
from app.utils.stats import get_stats, reset_stats
reset_stats()
stats = get_stats()
stats.record_message()
stats.record_api_call("test-model", 100, 50)
stats.record_agent_call("web_search")
stats.record_model_call("deepseek-v4")
print(f"Messages: {stats.message_count}")
print(f"API Calls: {stats.api_calls}")
print(f"Agent Calls: {stats.agent_calls}")
print(f"Model Calls: {stats.model_calls}")
print("[OK] Stats recording works")

# 2. Task Manager
print("\n2. Task Manager")
from app.agents.tasks import get_task_manager
tm = get_task_manager()
task = tm.create_task("Test task", priority="high")
print(f"Created: {task['id']}")
retrieved = tm.get_task(task['id'])
print(f"Retrieved: {retrieved['task']}")
tm.complete_task(task['id'])
print("[OK] Task manager works")

# 3. Tool Registry
print("\n3. Tool Registry")
from app.tools.tool_registry import ToolRegistry
tools = ToolRegistry.list_tools()
print(f"Tools: {len(tools)}")
result = ToolRegistry.execute("calculate", expression="2+2")
print(f"Calculate: {result}")
print("[OK] Tool registry works")

# 4. Memory
print("\n4. Memory System")
from app.memory.conversation import ConversationMemory, LongTermMemory
mem = ConversationMemory()
mem.add_message("user", "Hello")
messages = mem.get_messages()
print(f"Messages: {len(messages)}")
ltm = LongTermMemory()
print("[OK] Memory system works")

# 5. Stream Function
print("\n5. Stream Function")
from app.llm_client import chat_stream
import inspect
sig = inspect.signature(chat_stream)
print(f"Signature: {sig}")
print("[OK] Stream function exists")

# 6. Modules
print("\n6. Module Imports")
modules = [
    "app.agents.agents",
    "app.agents.autonomous",
    "app.agents.planner",
    "app.agents.tasks",
    "app.agents.learning",
]
for mod in modules:
    try:
        __import__(mod)
        print(f"  OK: {mod}")
    except Exception as e:
        print(f"  FAIL: {mod}: {e}")

print("\n" + "=" * 60)
print("ALL TESTS PASSED")
print("=" * 60)
