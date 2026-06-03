from app.memory.conversation import LongTermMemory

ltm = LongTermMemory()
print('LongTermMemory: OK')
print(f'Has update_preference: {hasattr(ltm, "update_preference")}')
print(f'Has record_tool_usage: {hasattr(ltm, "record_tool_usage")}')
print(f'Has get_profile_context: {hasattr(ltm, "get_profile_context")}')
