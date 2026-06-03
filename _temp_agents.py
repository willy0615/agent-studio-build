from app.agents.prompts import SUPERVISOR_SYSTEM_PROMPT, RESEARCHER_SYSTEM_PROMPT, CODER_SYSTEM_PROMPT, ANALYST_SYSTEM_PROMPT
from app.llm_client import chat_completion, chat_stream
from app.tools.web_search import search_web, fetch_url
from app.tools.code_executor import execute_code
from app.rag.retriever import rag_retrieve
import re
import time
import logging

logger = logging.getLogger(__name__)


# 🔧 优化: 关键词路由规则（省掉一次LLM调用）
ROUTING_KEYWORDS = {
    "researcher": [
        "搜索", "查找", "最新", "新闻", "资讯", "search", "find", "latest", "news",
        "什么是", "介绍一下", "告诉我", "查询", "调研", "研究", "了解",
    ],
    "coder": [
        "代码", "写程序", "python", "javascript", "编程", "实现", "code", "script",
        "写一个", "帮我写", "程序", "函数", "算法", "leetcode", "debug", "调试",
    ],
    "analyst": [
        "分析", "比较", "总结", "对比", "评估", "analyze", "compare", "summary",
        "优缺点", "利弊", "建议", "怎么看", "为什么", "原因", "趋势",
    ],
}


def route_to_agent(user_message: str, model: str = None) -> str:
    """Route to appropriate agent using keyword matching first, then LLM fallback."""
    msg_lower = user_message.lower()
    
    # 1. 关键词快速路由
    for agent, keywords in ROUTING_KEYWORDS.items():
        for kw in keywords:
            if kw in msg_lower:
                logger.info(f"Routed to {agent} via keyword: {kw}")
                return agent
    
    # 2. LLM路由兜底
    messages = [
        {"role": "system", "content": SUPERVISOR_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
    try:
        response = chat_completion(messages, model=model, temperature=0.1, max_retries=2)
        agent_name = response.choices[0].message.content.strip().lower()
        # Validate
        valid_agents = ["researcher", "coder", "analyst", "general"]
        for agent in valid_agents:
            if agent in agent_name:
                return agent
    except Exception as e:
        logger.warning(f"LLM routing failed: {e}")
    
    return "general"


def run_researcher(user_message: str, model: str = None, history: list = None) -> str:
    """Research Agent: search web + RAG knowledge base."""
    messages = [{"role": "system", "content": RESEARCHER_SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    
    # 并行获取上下文
    context_parts = []
    
    # RAG检索
    try:
        rag_context = rag_retrieve(user_message)
        if rag_context:
            context_parts.append(f"[Knowledge Base]\n{rag_context}")
    except Exception as e:
        logger.warning(f"RAG error: {e}")
    
    # Web搜索
    try:
        search_results = search_web(user_message)
        if search_results:
            web_context = "\n".join([
                f"- {r['title']}: {r['snippet']}"
                for r in search_results[:3]
            ])
            context_parts.append(f"[Web Search]\n{web_context}")
    except Exception as e:
        logger.warning(f"Web search error: {e}")
    
    # 构建增强消息
    enhanced_message = user_message
    if context_parts:
        enhanced_message += "\n\n--- Context ---\n" + "\n\n".join(context_parts)
    
    messages.append({"role": "user", "content": enhanced_message})
    
    response = chat_completion(messages, model=model)
    return response.choices[0].message.content


def run_coder(user_message: str, model: str = None, history: list = None) -> str:
    """Coder Agent: generate and execute code."""
    messages = [{"role": "system", "content": CODER_SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    response = chat_completion(messages, model=model)
    reply = response.choices[0].message.content

    # Extract and execute code blocks
    code_blocks = re.findall(r'```python\n(.*?)```', reply, re.DOTALL)
    execution_results = []
    
    for code in code_blocks:
        result = execute_code(code.strip())
        exec_output = ""
        if result["stdout"]:
            exec_output += f"Output:\n{result['stdout']}\n"
        if result["stderr"]:
            exec_output += f"Errors:\n{result['stderr']}\n"
        if exec_output:
            execution_results.append(exec_output)

    if execution_results:
        reply += "\n\n--- Execution Results ---\n" + "\n".join(execution_results)

    return reply


def run_analyst(user_message: str, model: str = None, history: list = None) -> str:
    """Analyst Agent: logical analysis and reasoning."""
    messages = [{"role": "system", "content": ANALYST_SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    response = chat_completion(messages, model=model)
    return response.choices[0].message.content


def run_general(user_message: str, model: str = None, history: list = None) -> str:
    """General conversation handler."""
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant. Answer concisely and clearly in the same language the user uses."},
    ]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    response = chat_completion(messages, model=model)
    return response.choices[0].message.content


# Agent dispatcher
AGENT_FUNCS = {
    "researcher": run_researcher,
    "coder": run_coder,
    "analyst": run_analyst,
    "general": run_general,
}


def process_message(user_message: str, model: str = None, history: list = None) -> dict:
    """Process a message through the multi-agent system.

    Returns: {"agent": str, "response": str, "time_ms": int}
    """
    start_time = time.time()
    
    agent_name = route_to_agent(user_message, model=model)
    func = AGENT_FUNCS.get(agent_name, run_general)
    
    try:
        response = func(user_message, model=model, history=history)
    except Exception as e:
        logger.error(f"Agent {agent_name} failed: {e}")
        # Fallback to general
        response = run_general(user_message, model=model, history=history)
        agent_name = "general (fallback)"
    
    elapsed_ms = int((time.time() - start_time) * 1000)
    
    return {
        "agent": agent_name,
        "response": response,
        "time_ms": elapsed_ms,
    }
