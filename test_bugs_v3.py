"""代码逻辑BUG检查 - 无Unicode字符"""
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("1. Check llm_client singleton")
print("=" * 60)

from app.llm_client import get_llm_client

client1 = get_llm_client()
client2 = get_llm_client()
print(f"Singleton OK: {id(client1) == id(client2)}")

print("\n" + "=" * 60)
print("2. Check code executor sandbox")
print("=" * 60)

from app.tools.code_executor import execute_code, _check_safety

# Test dangerous code blocking
tests = [
    ("import os\nos.system('rm -rf /')", "os.system"),
    ("import subprocess\nsubprocess.run(['cmd'])", "subprocess"),
    ("open('/etc/passwd', 'w')", "file write"),
    ("eval('__import__(\"os\")')", "eval"),
    ("exec('import os')", "exec"),
]

bugs = []
for code, desc in tests:
    is_safe, error = _check_safety(code)
    if is_safe:
        bugs.append(f"{desc}: NOT BLOCKED!")
    else:
        print(f"PASS: {desc} blocked")

if bugs:
    print("BUGS:")
    for b in bugs:
        print(f"  - {b}")
else:
    print("All dangerous code blocked")

# Test safe code
result = execute_code("print(1 + 1)")
print(f"Safe code result: {result}")

print("\n" + "=" * 60)
print("3. Check memory compression")
print("=" * 60)

from app.memory.conversation import ConversationMemory

mem = ConversationMemory()
mem.max_turns = 5

for i in range(20):
    mem.add_message("user", f"Message {i}" * 10)
    mem.add_message("assistant", f"Response {i}" * 10)

print(f"Added: 40 messages")
print(f"After compression: {len(mem.messages)}")

if len(mem.messages) > mem.max_turns * 2:
    print("BUG: Memory not compressed!")
else:
    print("PASS: Memory compressed correctly")

print("\n" + "=" * 60)
print("4. Check multi-agent")
print("=" * 60)

from app.agents.multi_agent import MultiAgentOrchestrator

orchestrator = MultiAgentOrchestrator()
agents = list(orchestrator.agents.keys())
print(f"Registered agents: {agents}")

required = ["coordinator", "researcher", "coder", "analyst", "reviewer"]
missing = [a for a in required if a not in agents]
if missing:
    print(f"BUG: Missing agents: {missing}")
else:
    print("PASS: All agents registered")

print("\n" + "=" * 60)
print("5. Check learning module")
print("=" * 60)

from app.agents.learning import get_skill_learner

learner = get_skill_learner()
learner.record_feedback("test", "good", "positive")
learner.record_feedback("test", "bad", "negative")

stats = learner.get_stats()
print(f"Stats: {stats}")

if stats["total_feedback"] == 2:
    print("PASS: Feedback recording works")
else:
    print("BUG: Feedback count mismatch")

print("\n" + "=" * 60)
print("6. Check tools registration")
print("=" * 60)

from app.tools.tool_registry import ToolRegistry

tools = ToolRegistry.list_tools()
print(f"Tools count: {len(tools)}")

bugs = []
for tool in tools:
    if "name" not in tool:
        bugs.append("Tool missing name")
    if "description" not in tool:
        bugs.append(f"Tool {tool.get('name')} missing description")
    if "parameters" not in tool:
        bugs.append(f"Tool {tool.get('name')} missing parameters")

if bugs:
    for b in bugs:
        print(f"BUG: {b}")
else:
    print("PASS: All tools have required fields")

print("\n" + "=" * 60)
print("7. Check complexity detection")
print("=" * 60)

from app.agents.autonomous import AutonomousAgent

agent = AutonomousAgent(mode='auto')

test_cases = [
    ("Hello", "simple"),
    ("Introduce Python", "simple"),
    ("Write a Python program", "complex"),
    ("Search latest AI news", "complex"),
    ("Deep research on AI Agent trends", "multi"),
]

failed = []
for task, expected in test_cases:
    result = agent._detect_complexity(task)
    if result != expected:
        failed.append((task, result, expected))
    print(f"{'PASS' if result == expected else 'FAIL'}: '{task[:20]}...' -> {result} (expected: {expected})")

if failed:
    print(f"\n{len(failed)} tests failed")
else:
    print("\nAll tests passed")

print("\n" + "=" * 60)
print("8. Check stats module")
print("=" * 60)

from app.utils.stats import get_stats

stats = get_stats()
print(f"Message count: {stats.message_count}")

stats.record_message()
stats.record_agent_call("test")
stats.record_model_call("test_model")

print(f"After recording:")
print(f"  Messages: {stats.message_count}")
print(f"  Agent calls: {stats.agent_calls}")
print(f"  Model calls: {stats.model_calls}")

print("\n" + "=" * 60)
print("ALL CHECKS COMPLETED")
print("=" * 60)
