import sys
sys.path.insert(0, '.')

from app.agents.autonomous import AutonomousAgent
from app.tools.tool_registry import ToolRegistry

print('=== 工具注册检查 ===')
tools = ToolRegistry.list_tools()
print(f'已注册工具: {len(tools)}个')
for t in tools:
    print(f'  - {t["name"]}')

print()
print('=== 执行简单任务测试 ===')
agent = AutonomousAgent(mode='simple')

result = agent.run(
    task='你好，介绍一下你自己',
    enable_reflection=False,
)

print(f'Mode: {result["mode"]}')
print(f'Success: {result["success"]}')
print(f'Answer: {result["answer"][:200]}...')
print(f'Time: {result["time_ms"]}ms')
