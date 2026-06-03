from openai import OpenAI
from app.config import NVIDIA_API_KEY, NVIDIA_BASE_URL, DEFAULT_MODEL
import time
import logging

logger = logging.getLogger(__name__)

# 🔧 优化1: 单例客户端 - 只创建一次，复用连接池
_client: OpenAI = None

def get_llm_client() -> OpenAI:
    """Get or create singleton OpenAI client."""
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=NVIDIA_API_KEY,
            base_url=NVIDIA_BASE_URL,
            timeout=60.0,
            max_retries=3,  # OpenAI SDK内置重试
        )
    return _client


def chat_completion(messages: list, model: str = None, temperature: float = 0.7,
                    stream: bool = False, max_retries: int = 3, **kwargs):
    """Send chat completion request to NVIDIA NIM with retry logic."""
    client = get_llm_client()
    model = model or DEFAULT_MODEL
    
    # 记录模型调用
    from app.utils.stats import get_stats
    get_stats().record_model_call(model)
    
    last_error = None
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                stream=stream,
                **kwargs,
            )
            # 记录API调用
            tokens_estimate = sum(len(str(m.get("content", ""))) for m in messages) // 4
            get_stats().record_api_call(model, tokens_estimate, 0)
            return response
        except Exception as e:
            last_error = e
            logger.warning(f"API call failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数退避
    
    raise RuntimeError(f"API call failed after {max_retries} retries: {last_error}")


def chat_stream(messages: list, model: str = None, temperature: float = 0.7, **kwargs):
    """Stream chat completion from NVIDIA NIM."""
    client = get_llm_client()
    model = model or DEFAULT_MODEL
    
    # 记录模型调用
    from app.utils.stats import get_stats
    get_stats().record_model_call(model)
    
    try:
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            stream=True,
            **kwargs,
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
        
        # 记录API调用
        tokens_estimate = sum(len(str(m.get("content", ""))) for m in messages) // 4
        get_stats().record_api_call(model, tokens_estimate, 0)
        
    except Exception as e:
        logger.error(f"Stream call failed: {e}")
        yield f"[Error: {e}]"
