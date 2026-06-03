import sys
sys.path.insert(0, r'E:\AgentProject')
try:
    from app.agents.autonomous import AutonomousAgent
    print("OK - AutonomousAgent imported successfully")
except Exception as e:
    print(f"ERROR: {e}")
