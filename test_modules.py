import sys
sys.path.insert(0, '.')

# 测试核心模块
from app.agents.autonomous import AutonomousAgent
from app.agents.learning import get_skill_learner
from app.agents.tasks import get_task_manager

print('=== 核心模块测试 ===')

# 测试学习模块
learner = get_skill_learner()
print(f'Learning stats: {learner.get_stats()}')

# 测试任务管理
task_mgr = get_task_manager()
print(f'Task stats: {task_mgr.get_stats()}')

# 测试复杂度检测
agent = AutonomousAgent(mode='auto')
test_tasks = [
    '你好',
    '帮我写一个Python程序计算斐波那契数列',
    '深入研究AI Agent的发展趋势，写一份综合报告',
]

print()
print('=== 复杂度检测测试 ===')
for task in test_tasks:
    complexity = agent._detect_complexity(task)
    print(f'{task[:30]}... -> {complexity}')

print()
print('=== 所有测试通过 ===')
