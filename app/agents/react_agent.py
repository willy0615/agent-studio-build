"""全能Agent核心 - ReAct循环"""
from app.llm_client import chat_completion
from app.tools.tool_registry import ToolRegistry
from typing import Dict, Any, List, Optional, Tuple
import json
import re
import time
import logging

logger = logging.getLogger(__name__)

# ReAct提示词
REACT_SYSTEM_PROMPT = """You are an autonomous AI agent that can think and act independently.

You have access to the following tools:
{tools_description}

Use the ReAct (Reasoning + Acting) pattern:

1. **Thought**: Think about what you need to do. Break down complex tasks.
2. **Action**: Choose a tool to use with appropriate parameters.
3. **Observation**: Review the tool's output.
4. **Repeat** until you have a complete answer.

**Important Rules**:
- Always plan before acting. Break complex tasks into steps.
- Use multiple tools in sequence if needed.
- If a tool fails, try alternative approaches.
- When you have enough information, provide a comprehensive final answer.
- Do not make up information. Use tools to verify facts.

Format your response as:
```
Thought: [your reasoning]
Action: {"tool": "tool_name", "parameters": {...}}
```

Or when done:
```
Thought: I have completed the task.
Final Answer: [comprehensive response]
```

Remember: You are autonomous. Take initiative, explore, verify, and iterate until you deliver high-quality results."""


class ReactAgent:
    """ReAct智能体 - 推理+行动循环"""
    
    def __init__(
        self,
        model: str = None,
        max_iterations: int = 10,
        verbose: bool = True,
    ):
        self.model = model
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.conversation_history: List[Dict] = []
        self.tool_calls: List[Dict] = []
    
    def _format_tools(self) -> str:
        """格式化工具描述"""
        tools = ToolRegistry.list_tools()
        lines = []
        for t in tools:
            params_desc = ", ".join(f"{k}: {v.get('type', 'any')}" for k, v in t["parameters"].items())
            lines.append(f"- {t['name']}({params_desc}): {t['description']}")
        return "\n".join(lines)
    
    def _parse_response(self, response: str) -> Tuple[Optional[str], Optional[Dict]]:
        """解析响应，提取Thought/Action/Final Answer"""
        thought = None
        action = None
        final_answer = None
        
        # 提取Thought
        thought_match = re.search(r'Thought:\s*(.+?)(?=\n(?:Action|Final)|$)', response, re.DOTALL)
        if thought_match:
            thought = thought_match.group(1).strip()
        
        # 提取Action
        action_match = re.search(r'Action:\s*({.+?})', response, re.DOTALL)
        if action_match:
            try:
                action = json.loads(action_match.group(1))
            except json.JSONDecodeError:
                # 尝试修复常见错误
                action_str = action_match.group(1)
                action_str = re.sub(r'(\w+):', r'"\1":', action_str)  # 给key加引号
                try:
                    action = json.loads(action_str)
                except:
                    logger.warning(f"Failed to parse action: {action_str}")
        
        # 提取Final Answer
        final_match = re.search(r'Final Answer:\s*(.+?)$', response, re.DOTALL)
        if final_match:
            final_answer = final_match.group(1).strip()
        
        return thought, action, final_answer
    
    def _execute_action(self, action: Dict) -> str:
        """执行工具调用"""
        tool_name = action.get("tool")
        parameters = action.get("parameters", {})
        
        if not tool_name:
            return "Error: No tool specified"
        
        result = ToolRegistry.execute(tool_name, **parameters)
        
        self.tool_calls.append({
            "tool": tool_name,
            "parameters": parameters,
            "result": result,
        })
        
        if result.get("success"):
            return f"Tool output: {json.dumps(result.get('result'), ensure_ascii=False, indent=2)[:2000]}"
        else:
            return f"Tool error: {result.get('error')}"
    
    def run(self, task: str, context: str = "") -> Dict[str, Any]:
        """执行ReAct循环
        
        Args:
            task: 用户任务
            context: 额外上下文（如对话历史、RAG知识等）
        
        Returns:
            {
                "success": bool,
                "answer": str,
                "tool_calls": list,
                "iterations": int,
                "time_ms": int,
            }
        """
        start_time = time.time()
        
        # 构建初始消息
        system_prompt = REACT_SYSTEM_PROMPT.format(tools_description=self._format_tools())
        user_message = f"Task: {task}"
        if context:
            user_message += f"\n\nContext:\n{context}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        
        self.conversation_history = messages.copy()
        self.tool_calls = []
        
        iteration = 0
        final_answer = None
        
        while iteration < self.max_iterations:
            iteration += 1
            
            if self.verbose:
                logger.info(f"=== Iteration {iteration} ===")
            
            # 调用LLM
            try:
                response = chat_completion(messages, model=self.model, temperature=0.7)
                assistant_message = response.choices[0].message.content
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                break
            
            messages.append({"role": "assistant", "content": assistant_message})
            
            # 解析响应
            thought, action, answer = self._parse_response(assistant_message)
            
            if self.verbose and thought:
                logger.info(f"Thought: {thought[:200]}")
            
            # 检查是否完成
            if answer:
                final_answer = answer
                break
            
            # 执行工具
            if action:
                observation = self._execute_action(action)
                if self.verbose:
                    logger.info(f"Action: {action.get('tool')} -> {observation[:200]}")
                
                messages.append({"role": "user", "content": f"Observation:\n{observation}"})
            else:
                # 没有有效行动，提示继续
                messages.append({
                    "role": "user",
                    "content": "Please either take an action or provide a final answer.",
                })
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        if not final_answer:
            # 达到最大迭代次数，强制总结
            if self.verbose:
                logger.info("Max iterations reached, forcing summary")
            try:
                summary_response = chat_completion(
                    messages + [{"role": "user", "content": "Please provide a final answer based on what you've learned."}],
                    model=self.model,
                )
                final_answer = summary_response.choices[0].message.content
            except:
                final_answer = "I was unable to complete the task within the iteration limit."
        
        return {
            "success": True,
            "answer": final_answer,
            "tool_calls": self.tool_calls,
            "iterations": iteration,
            "time_ms": elapsed_ms,
        }
