"""代码逻辑BUG检查"""
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("1. 检查llm_client单例模式")
print("=" * 60)

from app.llm_client import get_llm_client

# 测试单例
client1 = get_llm_client()
client2 = get_llm_client()
print(f"单例验证: {id(client1) == id(client2)}")
print(f"客户端类型: {type(client1)}")

print("\n" + "=" * 60)
print("2. 检查代码执行沙箱")
print("=" * 60)

from app.tools.code_executor import execute_code, _check_safety

# 测试危险代码拦截
tests = [
    ("import os\nos.system('rm -rf /')", "os.system"),
    ("import subprocess\nsubprocess.run(['cmd'])", "subprocess"),
    ("open('/etc/passwd', 'w')", "文件写入"),
    ("eval('__import__(\"os\")')", "eval"),
    ("exec('import os')", "exec"),
]

for code, desc in tests:
    is_safe, error = _check_safety(code)
    print(f"{desc}: {'✗ 拦截' if not is_safe else '✓ 放行'} - {error or 'OK'}")

# 测试安全代码执行
result = execute_code("print(1 + 1)")
print(f"\n安全代码执行: {result}")

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

# 验证不会无限增长
if len(mem.messages) > mem.max_turns * 2:
    print("⚠️ BUG: 记忆未正确压缩!")
else:
    print("✓ 记忆压缩正常")

print("\n" + "=" * 60)
print("4. 检查任务规划逻辑")
print("=" * 60)

from app.agents.planner import TaskPlanner

planner = TaskPlanner()

# 测试空任务
result = planner.plan("")
print(f"空任务: {result}")

# 测试简单任务
result = planner.plan("计算1+1")
print(f"简单任务: {result}")

print("\n" + "=" * 60)
print("5. 检查多Agent协作逻辑")
print("=" * 60)

from app.agents.multi_agent import MultiAgentOrchestrator

orchestrator = MultiAgentOrchestrator()

# 检查Agent注册
agents = list(orchestrator.agents.keys())
print(f"已注册Agent: {agents}")

# 检查工作流
print(f"工作流步骤: {orchestrator.workflow}")

# 验证必需Agent
required = ["coordinator", "researcher", "coder", "analyst", "reviewer"]
missing = [a for a in required if a not in agents]
if missing:
    print(f"⚠️ BUG: 缺少Agent: {missing}")
else:
    print("✓ 所有Agent已注册")

print("\n" + "=" * 60)
print("6. 检查学习模块")
print("=" * 60)

from app.agents.learning import get_skill_learner

learner = get_skill_learner()
stats = learner.get_stats()
print(f"初始统计: {stats}")

# 测试记录反馈
learner.record_feedback("test task", "good response", "positive")
learner.record_feedback("test task", "bad response", "negative")

stats = learner.get_stats()
print(f"记录反馈后: {stats}")

# 验证统计正确
if stats["total_feedback"] == 2 and stats["positive"] == 1 and stats["negative"] == 1:
    print("✓ 反馈记录正常")
else:
    print("⚠️ BUG: 反馈统计错误")

print("\n" + "=" * 60)
print("7. 检查工具注册完整性")
print("=" * 60)

from app.tools.tool_registry import ToolRegistry

tools = ToolRegistry.list_tools()
print(f"注册工具数: {len(tools)}")

# 验证每个工具都有必需字段
bugs = []
for tool in tools:
    if "name" not in tool:
        bugs.append("工具缺少name字段")
    if "description" not in tool:
        bugs.append(f"工具{tool.get('name')}缺少description")
    if "parameters" not in tool:
        bugs.append(f"工具{tool.get('name')}缺少parameters")

if bugs:
    print(f"⚠️ BUG:\n" + "\n".join(bugs))
else:
    print("✓ 所有工具字段完整")
    for tool in tools:
        print(f"  - {tool['name']}")

print("\n" + "=" * 60)
print("8. 检查复杂度检测")
print("=" * 60)

from app.agents.autonomous import AutonomousAgent

agent = AutonomousAgent(mode='auto')

test_cases = [
    ("你好", "simple"),
    ("介绍一下Python", "simple"),
    ("帮我写一个Python程序", "complex"),
    ("搜索最新的AI新闻", "complex"),  # 这个之前失败
    ("深入研究AI Agent的发展趋势", "multi"),
]

failed = []
for task, expected in test_cases:
    result = agent._detect_complexity(task)
    status = "✓" if result == expected else "✗"
    if result != expected:
        failed.append((task, result, expected))
    print(f"{status} '{task[:25]}...' -> {result} (预期: {expected})")

if failed:
    print(f"\n⚠️ {len(failed)}个测试失败")
else:
    print("\n✓ 复杂度检测正常")

print("\n" + "=" * 60)
print("9. 检查统计模块")
print("=" * 60)

from app.utils.stats import get_stats, reset_stats

stats = get_stats()
print(f"消息数: {stats.message_count}")
print(f"Agent调用: {stats.agent_calls}")
print(f"模型调用: {stats.model_calls}")

# 测试记录
stats.record_message()
stats.record_agent_call("test_agent")
stats.record_model_call("test_model")

print(f"\n记录后:")
print(f"消息数: {stats.message_count}")
print(f"Agent调用: {stats.agent_calls}")
print(f"模型调用: {stats.model_calls}")

# 测试保存
stats.save()
print("✓ 统计保存成功")

print("\n" + "=" * 60)
print("所有检查完成!")
print("=" * 60)
