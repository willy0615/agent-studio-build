import sys
sys.path.insert(0, '.')

# 测试所有关键导入
imports = [
    ('app.config', 'config'),
    ('app.llm_client', 'llm_client'),
    ('app.tools.tool_registry', 'tool_registry'),
    ('app.tools.web_search', 'web_search'),
    ('app.tools.code_executor', 'code_executor'),
    ('app.tools.file_ops', 'file_ops'),
    ('app.tools.api_caller', 'api_caller'),
    ('app.tools.data_processor', 'data_processor'),
    ('app.agents.autonomous', 'autonomous'),
    ('app.agents.react_agent', 'react_agent'),
    ('app.agents.planner', 'planner'),
    ('app.agents.reflection', 'reflection'),
    ('app.agents.multi_agent', 'multi_agent'),
    ('app.agents.learning', 'learning'),
    ('app.agents.tasks', 'tasks'),
    ('app.rag.vectorstore', 'vectorstore'),
    ('app.rag.retriever', 'retriever'),
    ('app.memory.conversation', 'conversation'),
    ('app.utils.stats', 'stats'),
]

failed = []
for module, name in imports:
    try:
        __import__(module)
        print(f'OK {name}')
    except Exception as e:
        print(f'FAIL {name}: {e}')
        failed.append((name, str(e)))

if failed:
    print(f'\nFailed: {len(failed)}')
    sys.exit(1)
else:
    print(f'\nAll {len(imports)} modules imported successfully')
