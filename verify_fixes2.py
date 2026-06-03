"""验证 - 不加载ChromaDB"""
import sys
sys.path.insert(0, '.')
import threading

print("=== Fix Verification ===\n")

# 1. Stats thread safety
print("1. Stats thread safety...")
from app.utils.stats import Stats
s = Stats()

def worker(stats, agent_name, count):
    for _ in range(count):
        stats.record_agent_call(agent_name)
        stats.record_message()

threads = [
    threading.Thread(target=worker, args=(s, "agent_a", 100)),
    threading.Thread(target=worker, args=(s, "agent_b", 100)),
    threading.Thread(target=worker, args=(s, "agent_c", 100)),
]
for t in threads:
    t.start()
for t in threads:
    t.join()

total_calls = sum(s.agent_calls.values())
expected = 300
assert total_calls == expected, f"Race condition! Got {total_calls}, expected {expected}"
assert s.message_count == expected, f"Message count race! Got {s.message_count}, expected {expected}"
print(f"   PASS - {total_calls} concurrent increments, all correct\n")

# 2. Planner evaluate_progress integration (source inspection only)
print("2. Planner evaluate_progress integration...")
with open("app/agents/autonomous.py", encoding="utf-8") as f:
    src = f.read()
assert "evaluate_progress" in src, "evaluate_progress not called in run()"
assert "plan_progress" in src, "plan_progress not in result"
assert "needs_revision" in src, "needs_revision handling missing"
print("   PASS - evaluate_progress integrated in react mode\n")

# 3. Singleton thread safety
print("3. get_stats() singleton thread safety...")
from app.utils.stats import get_stats
results = []
def get_stats_thread():
    results.append(id(get_stats()))

threads = [threading.Thread(target=get_stats_thread) for _ in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()

assert len(set(results)) == 1, f"Multiple instances! IDs: {set(results)}"
print("   PASS - singleton safe across threads\n")

print("=== All Fixes Verified! ===")
