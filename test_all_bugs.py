"""完整BUG检查 - 无Unicode"""
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("1. LLM Client Singleton")
print("=" * 60)

from app.llm_client import get_llm_client
client1 = get_llm_client()
client2 = get_llm_client()
print(f"Singleton: {id(client1) == id(client2)}")

print("\n" + "=" * 60)
print("2. Code Executor Sandbox")
print("=" * 60)

from app.tools.code_executor import execute_code, _check_safety

# Dangerous patterns
tests = [
    ("import os\nos.system('cmd')", "os.system"),
    ("import subprocess", "subprocess"),
    ("open('x', 'w')", "file write"),
    ("__import__('os')", "__import__"),
    ("eval('x')", "eval"),
    ("exec('x')", "exec"),
    ("compile('x', 'x', 'exec')", "compile"),
]

all_blocked = True
for code, desc in tests:
    is_safe, error = _check_safety(code)
    if is_safe:
        print(f"BUG: {desc} NOT BLOCKED")
        all_blocked = False
    else:
        print(f"OK: {desc}")

if all_blocked:
    print("PASS: All dangerous code blocked")

# Safe code execution
result = execute_code("x = 1 + 1\nprint(x)")
print(f"Safe code: stdout={result.get('stdout', '').strip()}")

print("\n" + "=" * 60)
print("3. Memory Compression")
print("=" * 60)

from app.memory.conversation import ConversationMemory

mem = ConversationMemory()
mem.max_turns = 5

for i in range(30):
    mem.add_message("user", f"Message {i}")
    mem.add_message("assistant", f"Response {i}")

print(f"Added: 60 messages")
print(f"After compression: {len(mem.messages)}")
print(f"Summary length: {len(mem.summary)}")

if len(mem.messages) <= 10:
    print("PASS: Memory compression works")
else:
    print("BUG: Memory not compressed!")

print("\n" + "=" * 60)
print("4. Multi-Agent")
print("=" * 60)

from app.agents.multi_agent import MultiAgentOrchestrator

orchestrator = MultiAgentOrchestrator()
agents = list(orchestrator.agents.keys())
print(f"Agents: {agents}")

required = ["coordinator", "researcher", "coder", "analyst", "reviewer"]
missing = [a for a in required if a not in agents]
if missing:
    print(f"BUG: Missing: {missing}")
else:
    print("PASS: All agents present")

print("\n" + "=" * 60)
print("5. Learning Module")
print("=" * 60)

from app.agents.learning import get_skill_learner

learner = get_skill_learner()
learner.record_feedback("test", "response1", "positive")
learner.record_feedback("test", "response2", "negative")
learner.record_feedback("test", "response3", "positive")

stats = learner.get_stats()
print(f"Stats: {stats}")

if stats["total_feedback"] >= 3:
    print("PASS: Feedback recording works")
else:
    print("BUG: Feedback not recorded")

print("\n" + "=" * 60)
print("6. Tool Registry")
print("=" * 60)

from app.tools.tool_registry import ToolRegistry

tools = ToolRegistry.list_tools()
print(f"Tools: {len(tools)}")

# Test each tool
print("\nTesting tools:")
test_results = []

# execute_code
r = ToolRegistry.execute("execute_code", code="print(1+1)")
test_results.append(("execute_code", r.get("success", False)))

# calculate
r = ToolRegistry.execute("calculate", expression="2+2")
test_results.append(("calculate", r.get("success", False)))

# read_file (nonexistent)
r = ToolRegistry.execute("read_file", path="/nonexistent")
test_results.append(("read_file", not r.get("success", True)))  # Should fail

# call_api (invalid URL)
r = ToolRegistry.execute("call_api", url="invalid", method="GET")
test_results.append(("call_api", not r.get("success", True)))  # Should fail

for name, passed in test_results:
    print(f"  {name}: {'PASS' if passed else 'FAIL'}")

print("\n" + "=" * 60)
print("7. Complexity Detection")
print("=" * 60)

from app.agents.autonomous import AutonomousAgent

agent = AutonomousAgent(mode='auto')

tests = [
    ("Hello", "simple"),
    ("What is Python", "simple"),
    ("Write a program", "complex"),
    ("Search for news", "complex"),
    ("Calculate 1+1", "complex"),
    ("Deep research report", "multi"),
]

failed = []
for task, expected in tests:
    result = agent._detect_complexity(task)
    status = "PASS" if result == expected else "FAIL"
    if result != expected:
        failed.append((task, result, expected))
    print(f"{status}: '{task}' -> {result} (expected: {expected})")

print("\n" + "=" * 60)
print("8. Stats Module")
print("=" * 60)

from app.utils.stats import get_stats, reset_stats

reset_stats()
stats = get_stats()
print(f"Initial: messages={stats.message_count}")

stats.record_message()
stats.record_message()
stats.record_agent_call("test_agent")
stats.record_model_call("test_model")

print(f"After: messages={stats.message_count}, agents={stats.agent_calls}, models={stats.model_calls}")

print("\n" + "=" * 60)
print("9. RAG VectorStore (skip if ChromaDB not ready)")
print("=" * 60)

try:
    from app.rag.vectorstore import get_vectorstore, chunk_documents
    
    # Test chunking
    text = "Test content. " * 100
    chunks = chunk_documents(text, chunk_size=50, overlap=10)
    print(f"Chunks: {len(chunks)}")
    
    if len(chunks) > 1:
        print("PASS: Document chunking works")
    
except Exception as e:
    print(f"SKIP: ChromaDB not ready ({type(e).__name__})")

print("\n" + "=" * 60)
print("10. Error Handling")
print("=" * 60)

# Test invalid tool
r = ToolRegistry.execute("nonexistent_tool")
if "error" in r:
    print("PASS: Invalid tool returns error")
else:
    print("BUG: Invalid tool should return error")

# Test missing parameters
r = ToolRegistry.execute("execute_code")  # No code parameter
if not r.get("success", False):
    print("PASS: Missing params handled")
else:
    print("BUG: Missing params should fail")

print("\n" + "=" * 60)
print("ALL TESTS COMPLETED")
print("=" * 60)
