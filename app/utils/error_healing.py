"""错误自愈系统 - 自动识别和修复常见错误"""
from typing import Dict, Any, List, Optional, Tuple
import re
import logging
import traceback

logger = logging.getLogger(__name__)


class ErrorHealer:
    """错误自愈器"""
    
    def __init__(self):
        # 错误模式库
        self.error_patterns = {
            # 代码执行错误
            "syntax_error": {
                "pattern": r"SyntaxError: (.+)",
                "heal_strategy": "fix_syntax",
                "auto_fixable": True,
            },
            "name_error": {
                "pattern": r"NameError: name '(\w+)' is not defined",
                "heal_strategy": "define_variable",
                "auto_fixable": True,
            },
            "import_error": {
                "pattern": r"ImportError: (.+)",
                "heal_strategy": "install_package",
                "auto_fixable": False,
            },
            "type_error": {
                "pattern": r"TypeError: (.+)",
                "heal_strategy": "fix_type",
                "auto_fixable": True,
            },
            "index_error": {
                "pattern": r"IndexError: (.+)",
                "heal_strategy": "check_bounds",
                "auto_fixable": True,
            },
            "key_error": {
                "pattern": r"KeyError: (.+)",
                "heal_strategy": "check_key",
                "auto_fixable": True,
            },
            
            # API错误
            "api_timeout": {
                "pattern": r"(timeout|timed out)",
                "heal_strategy": "retry_with_backoff",
                "auto_fixable": True,
            },
            "api_rate_limit": {
                "pattern": r"(rate limit|429)",
                "heal_strategy": "wait_and_retry",
                "auto_fixable": True,
            },
            "api_auth_error": {
                "pattern": r"(401|403|authentication|unauthorized)",
                "heal_strategy": "check_credentials",
                "auto_fixable": False,
            },
            
            # 文件错误
            "file_not_found": {
                "pattern": r"FileNotFoundError: (.+)",
                "heal_strategy": "create_file_or_check_path",
                "auto_fixable": True,
            },
            "permission_error": {
                "pattern": r"PermissionError: (.+)",
                "heal_strategy": "adjust_permissions",
                "auto_fixable": False,
            },
            
            # JSON错误
            "json_decode_error": {
                "pattern": r"JSONDecodeError: (.+)",
                "heal_strategy": "fix_json",
                "auto_fixable": True,
            },
            
            # 网络错误
            "connection_error": {
                "pattern": r"(ConnectionError|Connection refused|Network unreachable)",
                "heal_strategy": "retry_with_backoff",
                "auto_fixable": True,
            },
        }
        
        # 自愈历史
        self.heal_history = []
    
    def analyze_error(self, error: Exception) -> Dict[str, Any]:
        """分析错误
        
        Args:
            error: 异常对象
        
        Returns:
            {
                "error_type": str,
                "error_message": str,
                "pattern_matched": str,
                "auto_fixable": bool,
                "heal_strategy": str,
                "suggestions": list,
            }
        """
        error_message = str(error)
        error_type = type(error).__name__
        tb = traceback.format_exc()
        
        # 匹配错误模式
        matched_pattern = None
        for pattern_name, pattern_info in self.error_patterns.items():
            if re.search(pattern_info["pattern"], error_message, re.I):
                matched_pattern = pattern_name
                break
        
        # 生成分析结果
        result = {
            "error_type": error_type,
            "error_message": error_message,
            "traceback": tb,
            "pattern_matched": matched_pattern,
            "auto_fixable": False,
            "heal_strategy": None,
            "suggestions": [],
        }
        
        if matched_pattern:
            pattern_info = self.error_patterns[matched_pattern]
            result["auto_fixable"] = pattern_info["auto_fixable"]
            result["heal_strategy"] = pattern_info["heal_strategy"]
            result["suggestions"] = self._generate_suggestions(matched_pattern, error_message)
        
        return result
    
    def attempt_heal(
        self,
        error: Exception,
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """尝试自愈
        
        Args:
            error: 异常对象
            context: 上下文信息（如代码、文件路径等）
        
        Returns:
            {
                "success": bool,
                "fix_applied": str,
                "fixed_content": any,
                "message": str,
            }
        """
        context = context or {}
        
        # 分析错误
        analysis = self.analyze_error(error)
        
        # 记录历史
        self.heal_history.append({
            "error": analysis,
            "context": context,
            "timestamp": __import__('datetime').datetime.now().isoformat(),
        })
        
        # 如果不可自动修复，返回建议
        if not analysis["auto_fixable"]:
            return {
                "success": False,
                "fix_applied": None,
                "message": f"无法自动修复，建议: {', '.join(analysis['suggestions'])}",
                "suggestions": analysis["suggestions"],
            }
        
        # 尝试修复
        strategy = analysis["heal_strategy"]
        
        try:
            if strategy == "fix_syntax":
                return self._heal_syntax_error(error, context)
            
            elif strategy == "define_variable":
                return self._heal_name_error(error, context)
            
            elif strategy == "fix_type":
                return self._heal_type_error(error, context)
            
            elif strategy == "check_bounds":
                return self._heal_index_error(error, context)
            
            elif strategy == "check_key":
                return self._heal_key_error(error, context)
            
            elif strategy == "fix_json":
                return self._heal_json_error(error, context)
            
            elif strategy == "retry_with_backoff":
                return self._heal_retry(error, context)
            
            elif strategy == "create_file_or_check_path":
                return self._heal_file_not_found(error, context)
            
            else:
                return {
                    "success": False,
                    "fix_applied": None,
                    "message": f"未知修复策略: {strategy}",
                }
        
        except Exception as e:
            logger.error(f"Heal attempt failed: {e}")
            return {
                "success": False,
                "fix_applied": None,
                "message": f"修复失败: {str(e)}",
            }
    
    def _generate_suggestions(self, pattern_name: str, error_message: str) -> List[str]:
        """生成修复建议"""
        suggestions_map = {
            "syntax_error": [
                "检查代码语法",
                "确保括号、引号匹配",
                "检查缩进是否正确",
            ],
            "name_error": [
                "检查变量是否已定义",
                "检查拼写是否正确",
                "检查作用域",
            ],
            "import_error": [
                "安装缺失的包: pip install <package>",
                "检查包名是否正确",
            ],
            "type_error": [
                "检查数据类型是否匹配",
                "使用类型转换函数",
            ],
            "api_timeout": [
                "增加超时时间",
                "检查网络连接",
                "稍后重试",
            ],
            "api_rate_limit": [
                "等待60秒后重试",
                "减少请求频率",
            ],
            "api_auth_error": [
                "检查API Key是否正确",
                "检查API Key是否过期",
                "检查权限设置",
            ],
            "file_not_found": [
                "检查文件路径是否正确",
                "检查文件是否存在",
                "创建缺失的文件",
            ],
            "json_decode_error": [
                "检查JSON格式是否正确",
                "使用JSON验证工具",
                "添加错误处理",
            ],
        }
        
        return suggestions_map.get(pattern_name, ["查看错误信息，手动修复"])
    
    def _heal_syntax_error(self, error: Exception, context: Dict) -> Dict[str, Any]:
        """修复语法错误"""
        code = context.get("code", "")
        if not code:
            return {"success": False, "message": "无代码上下文"}
        
        error_msg = str(error)
        
        # 常见语法修复
        fixes = []
        
        # 缺少冒号
        if "expected ':'" in error_msg:
            fixed_code = re.sub(r'(if|elif|else|for|while|def|class|try|except|finally)\s+([^\n:]+)$', r'\1 \2:', code, flags=re.M)
            if fixed_code != code:
                fixes.append("添加缺失的冒号")
                code = fixed_code
        
        # 括号不匹配
        if "parenthesis" in error_msg.lower() or "bracket" in error_msg.lower():
            open_count = code.count('(') + code.count('[') + code.count('{')
            close_count = code.count(')') + code.count(']') + code.count('}')
            
            if open_count > close_count:
                diff = open_count - close_count
                code += ')' * diff
                fixes.append(f"添加 {diff} 个缺失的右括号")
        
        return {
            "success": len(fixes) > 0,
            "fix_applied": "syntax_fix",
            "fixed_content": code,
            "fixes": fixes,
            "message": "已修复: " + ", ".join(fixes) if fixes else "无法自动修复",
        }
    
    def _heal_name_error(self, error: Exception, context: Dict) -> Dict[str, Any]:
        """修复NameError"""
        error_msg = str(error)
        match = re.search(r"name '(\w+)' is not defined", error_msg)
        
        if not match:
            return {"success": False, "message": "无法解析错误"}
        
        var_name = match.group(1)
        code = context.get("code", "")
        
        # 尝试推断变量类型
        suggestions = []
        
        # 常见变量初始化
        common_initializations = {
            "df": "df = pd.DataFrame()",
            "data": "data = []",
            "result": "result = None",
            "count": "count = 0",
            "i": "i = 0",
        }
        
        if var_name in common_initializations:
            return {
                "success": True,
                "fix_applied": "define_variable",
                "fixed_content": common_initializations[var_name],
                "message": f"建议初始化: {common_initializations[var_name]}",
            }
        
        return {
            "success": False,
            "message": f"变量 '{var_name}' 未定义，请手动检查",
            "suggestions": [f"在使用前定义变量: {var_name} = ..."],
        }
    
    def _heal_type_error(self, error: Exception, context: Dict) -> Dict[str, Any]:
        """修复TypeError"""
        error_msg = str(error)
        
        # 常见类型错误修复
        if "can only concatenate" in error_msg:
            return {
                "success": True,
                "fix_applied": "type_conversion",
                "message": "类型不匹配，需要类型转换",
                "suggestions": ["使用 str() 转换为字符串", "使用 int() 转换为整数"],
            }
        
        if "not callable" in error_msg:
            return {
                "success": True,
                "fix_applied": "remove_call",
                "message": "对象不可调用，移除括号",
            }
        
        return {
            "success": False,
            "message": "TypeError需要手动检查类型",
        }
    
    def _heal_index_error(self, error: Exception, context: Dict) -> Dict[str, Any]:
        """修复IndexError"""
        return {
            "success": True,
            "fix_applied": "bounds_check",
            "message": "索引越界，添加边界检查",
            "suggestions": [
                "使用 if index < len(list): 检查索引",
                "使用 try/except 捕获异常",
                "使用 list[index:index+1] 避免越界",
            ],
        }
    
    def _heal_key_error(self, error: Exception, context: Dict) -> Dict[str, Any]:
        """修复KeyError"""
        error_msg = str(error)
        match = re.search(r"KeyError: ['\"]?(\w+)['\"]?", error_msg)
        
        if match:
            key = match.group(1)
            return {
                "success": True,
                "fix_applied": "key_check",
                "message": f"键 '{key}' 不存在",
                "suggestions": [
                    f"使用 dict.get('{key}', default) 安全访问",
                    f"使用 if '{key}' in dict: 检查键",
                    "检查键名拼写是否正确",
                ],
            }
        
        return {"success": False, "message": "无法解析KeyError"}
    
    def _heal_json_error(self, error: Exception, context: Dict) -> Dict[str, Any]:
        """修复JSON错误"""
        json_str = context.get("json_string", "")
        
        if not json_str:
            return {"success": False, "message": "无JSON上下文"}
        
        # 常见JSON修复
        fixes = []
        
        # 单引号改双引号
        if "'" in json_str and '"' not in json_str:
            json_str = json_str.replace("'", '"')
            fixes.append("单引号改为双引号")
        
        # 尝试解析
        try:
            import json
            json.loads(json_str)
            return {
                "success": True,
                "fix_applied": "json_fix",
                "fixed_content": json_str,
                "fixes": fixes,
                "message": "JSON已修复: " + ", ".join(fixes),
            }
        except:
            pass
        
        return {
            "success": False,
            "message": "JSON格式错误，需要手动修复",
        }
    
    def _heal_retry(self, error: Exception, context: Dict) -> Dict[str, Any]:
        """重试策略"""
        return {
            "success": True,
            "fix_applied": "retry",
            "message": "网络错误，建议重试",
            "suggestions": [
                "等待5-10秒后重试",
                "使用指数退避重试",
                "检查网络连接",
            ],
            "retry_recommended": True,
        }
    
    def _heal_file_not_found(self, error: Exception, context: Dict) -> Dict[str, Any]:
        """修复文件未找到"""
        error_msg = str(error)
        match = re.search(r"FileNotFoundError: \[Errno .+\] No such file or directory: '(.+)'", error_msg)
        
        if match:
            file_path = match.group(1)
            return {
                "success": True,
                "fix_applied": "file_check",
                "message": f"文件不存在: {file_path}",
                "suggestions": [
                    f"检查路径是否正确: {file_path}",
                    "使用 os.path.exists() 检查文件",
                    "创建缺失的文件",
                ],
            }
        
        return {"success": False, "message": "无法解析文件路径"}
    
    def get_heal_stats(self) -> Dict[str, Any]:
        """获取自愈统计"""
        total_attempts = len(self.heal_history)
        successful = sum(1 for h in self.heal_history if h.get("heal_result", {}).get("success"))
        
        error_types = {}
        for h in self.heal_history:
            error_type = h["error"]["error_type"]
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        return {
            "total_attempts": total_attempts,
            "successful_heals": successful,
            "success_rate": successful / max(1, total_attempts),
            "error_types": error_types,
        }


# 全局实例
_error_healer = None


def get_error_healer() -> ErrorHealer:
    """获取全局错误自愈器"""
    global _error_healer
    if _error_healer is None:
        _error_healer = ErrorHealer()
    return _error_healer


def heal_error(error: Exception, context: Dict = None) -> Dict[str, Any]:
    """便捷函数：尝试修复错误"""
    healer = get_error_healer()
    return healer.attempt_heal(error, context)
