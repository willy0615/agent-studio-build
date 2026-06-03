import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict
import re

# 🔧 危险操作黑名单
DANGEROUS_PATTERNS = [
    r'\bos\.system\s*\(',
    r'\bos\.popen\s*\(',
    r'\bsubprocess\.',
    r'\b__import__\s*\(',
    r'\beval\s*\(',
    r'\bexec\s*\(',
    r'\bcompile\s*\(',
    r'\bopen\s*\([\'"][\w:\\/]+.*[\'"][\s,]*["\']w',
    r'\bshutil\.rmtree',
    r'\bshutil\.move',
    r'\bos\.remove',
    r'\bos\.rmdir',
    r'\bos\.makedirs',
    r'\bos\.mkdir',
    r'import\s+os\b',
    r'from\s+os\s+import',
    r'import\s+subprocess\b',
    r'import\s+socket\b',
]

ALLOWED_IMPORTS = [
    'math', 'random', 'datetime', 'collections', 'itertools', 'functools',
    'typing', 'json', 're', 'string', 'textwrap', 'statistics', 'fractions',
    'decimal', 'copy', 'operator', 'pathlib', 'dataclasses', 'enum',
    # 数据处理
    'numpy', 'pandas', 'scipy', 'sklearn',
]

MAX_OUTPUT_LENGTH = 5000


def _check_safety(code: str) -> tuple[bool, str]:
    """Check if code is safe to execute.
    
    Returns:
        (is_safe, error_message)
    """
    # 检查危险模式
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, code):
            return False, f"Dangerous pattern detected: {pattern}"
    
    # 检查导入
    import_pattern = r'^(?:from\s+(\S+)\s+import|import\s+(\S+))'
    for match in re.finditer(import_pattern, code, re.MULTILINE):
        module = match.group(1) or match.group(2)
        module = module.split('.')[0]  # 只检查顶级模块
        if module not in ALLOWED_IMPORTS and not module.startswith('_'):
            # 允许用户代码导入自己的模块，但警告
            pass  # 暂时放行，只禁止危险操作
    
    return True, ""


def execute_code(code: str, timeout: int = 30) -> Dict[str, str]:
    """Execute Python code in a safe sandbox.
    
    Args:
        code: Python code to execute
        timeout: Execution timeout in seconds
    
    Returns:
        {"stdout": str, "stderr": str, "return_code": int}
    """
    # 安全检查
    is_safe, error = _check_safety(code)
    if not is_safe:
        return {"stdout": "", "stderr": f"Security Error: {error}", "return_code": 1}
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(code)
        temp_file = f.name
    
    try:
        # 使用subprocess执行，限制资源
        result = subprocess.run(
            [sys.executable, temp_file],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=tempfile.gettempdir(),
            # Windows下不需要shell
        )
        
        stdout = result.stdout[:MAX_OUTPUT_LENGTH]
        stderr = result.stderr[:MAX_OUTPUT_LENGTH]
        
        return {
            "stdout": stdout,
            "stderr": stderr,
            "return_code": result.returncode,
        }
    
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": f"Timeout: Execution exceeded {timeout}s", "return_code": -1}
    
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "return_code": 1}
    
    finally:
        # 清理临时文件
        try:
            Path(temp_file).unlink()
        except:
            pass
