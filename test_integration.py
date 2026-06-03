from app.agents.planner import TaskPlanner
from app.agents.tasks import TaskPersistence
from app.utils.multimodal import get_multimodal_processor
from app.agents.multi_agent import MultiAgentOrchestrator
from app.utils.context_compression import get_compressor

print("1. Planner: OK")
planner = TaskPlanner()

print("2. Tasks: OK")
task_mgr = TaskPersistence()

print("3. Multimodal: OK")
processor = get_multimodal_processor()

print("4. Multi-Agent: OK")
orchestrator = MultiAgentOrchestrator()

print("5. Context Compression: OK")
compressor = get_compressor()

print("\nAll modules loaded successfully!")
