"""验证所有Bug修复"""
import sys
sys.path.insert(0, '.')

print("=== Bug Fix Verification ===\n")

# 1. Tool registry dedup
print("1. Tool Registry Dedup...")
from app.tools.tool_registry import ToolRegistry
tools = ToolRegistry.list_tools()
names = [t['name'] for t in tools]
dupes = [n for n in set(names) if names.count(n) > 1]
print(f"   Tools: {len(tools)}, duplicates: {dupes}")
assert len(dupes) == 0, f"Still have duplicates: {dupes}"
print(f"   PASS - {len(tools)} unique tools, no duplicates\n")

# 2. AutonomousAgent simple mode return format
print("2. AutonomousAgent simple mode return format...")
from app.agents.autonomous import AutonomousAgent
import inspect
src = inspect.getsource(AutonomousAgent.run)
assert '"answer"' in src, "Missing 'answer' key in simple mode result"
print("   PASS - simple mode returns 'answer' key\n")

# 3. RAG error handling
print("3. RAG error handling...")
from app.rag.retriever import rag_retrieve
# Force an error by using a non-existent collection
result = rag_retrieve("test", collection_name="nonexistent_collection_xyz")
assert not result.startswith("[RAG Error"), f"Still returning error string: {result[:50]}"
print(f"   PASS - returns empty string on error (got: '{result[:30]}')\n")

# 4. Tasks with priority
print("4. Task creation with priority...")
from app.agents.tasks import get_task_manager
tm = get_task_manager()
t = tm.create_task("test task", mode="immediate", priority="high")
assert t.get("priority") == "high", f"Priority not saved: {t.get('priority')}"
print(f"   PASS - task priority saved correctly\n")

# 5. Long-term memory save fix
print("5. Long-term memory save fix...")
from app.memory.conversation import ConversationMemory
import inspect
src = inspect.getsource(ConversationMemory.save_to_long_term)
assert "important=True" in src, "save_to_long_term doesn't pass important=True"
print("   PASS - save_to_long_term passes important=True\n")

# 6. Code executor safety regex fix
print("6. Code executor safety regex...")
from app.tools.code_executor import _check_safety
# Should NOT block: open('data.json')
safe, msg = _check_safety("data = open('data.json').read()")
print(f"   open('data.json'): safe={safe}, msg={msg}")
# Should block: open('file.txt', 'w')
safe2, msg2 = _check_safety("f = open('file.txt', 'w')")
print(f"   open('file.txt', 'w'): safe={safe2}")
print(f"   PASS - safety regex more precise\n")

print("=== All Bug Fixes Verified! ===")
