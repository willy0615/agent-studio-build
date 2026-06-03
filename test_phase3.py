from app.monitoring.performance import get_monitor
from app.agents.quick_commands import get_quick_command_registry
from app.rag.knowledge_graph import get_visualizer

# 监控
m = get_monitor()
print('Monitor: OK')
sys_m = m.get_system_metrics()
print(f"CPU: {sys_m.get('cpu_percent', 0):.1f}%")
print(f"Memory: {sys_m.get('memory_percent', 0):.1f}%")

# 快捷命令
r = get_quick_command_registry()
print(f'Quick Commands: {len(r.list_commands())}')

# 知识图谱
v = get_visualizer()
print('Knowledge Graph: OK')

print('\nAll Phase 3 modules loaded successfully!')
