"""多模态输入处理器 - 统一处理文本/图像/音频/文档"""
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import tempfile
import logging
import base64
import mimetypes

logger = logging.getLogger(__name__)


class MultimodalInputProcessor:
    """多模态输入处理器"""
    
    def __init__(self):
        self.supported_types = {
            "image": ["jpg", "jpeg", "png", "gif", "webp", "bmp"],
            "audio": ["mp3", "wav", "m4a", "ogg", "flac"],
            "document": ["pdf", "docx", "doc", "txt", "md"],
            "data": ["xlsx", "xls", "csv", "json", "xml"],
            "code": ["py", "js", "ts", "java", "cpp", "c", "go", "rs"],
        }
    
    def detect_type(self, file_path: str) -> str:
        """检测文件类型
        
        Args:
            file_path: 文件路径
        
        Returns:
            类型: image | audio | document | data | code | unknown
        """
        ext = Path(file_path).suffix.lower().lstrip(".")
        
        for file_type, extensions in self.supported_types.items():
            if ext in extensions:
                return file_type
        
        return "unknown"
    
    def process(
        self,
        text: str = "",
        files: List[str] = None,
        file_objects: List[Dict] = None,
        auto_analyze: bool = True,
    ) -> Dict[str, Any]:
        """统一处理多模态输入
        
        Args:
            text: 文本输入
            files: 文件路径列表
            file_objects: 文件对象列表 [{"name": str, "data": bytes, "type": str}]
            auto_analyze: 是否自动分析文件
        
        Returns:
            {
                "success": bool,
                "text": str,  # 合并后的文本
                "context": str,  # 完整上下文
                "files_processed": list,  # 已处理文件列表
                "suggestions": list,  # 建议的操作
            }
        """
        files = files or []
        file_objects = file_objects or []
        
        all_files = []
        processed_files = []
        contexts = []
        suggestions = []
        
        # 处理文件路径
        for file_path in files:
            all_files.append({
                "path": file_path,
                "name": Path(file_path).name,
                "type": self.detect_type(file_path),
            })
        
        # 处理文件对象（从Streamlit上传）
        for file_obj in file_objects:
            # 保存到临时文件
            suffix = Path(file_obj["name"]).suffix
            temp_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix,
            )
            temp_file.write(file_obj["data"])
            temp_file.close()
            
            all_files.append({
                "path": temp_file.name,
                "name": file_obj["name"],
                "type": self.detect_type(file_obj["name"]),
            })
        
        # 处理每个文件
        for file_info in all_files:
            file_type = file_info["type"]
            file_path = file_info["path"]
            file_name = file_info["name"]
            
            if auto_analyze:
                result = self._analyze_file(file_path, file_type)
                
                processed_files.append({
                    "name": file_name,
                    "type": file_type,
                    "path": file_path,
                    "analysis": result,
                })
                
                # 添加上下文
                if result.get("success"):
                    contexts.append(f"[{file_type.upper()}: {file_name}]\\n{result['summary']}")
                    
                    # 生成建议
                    suggestions.extend(result.get("suggestions", []))
            else:
                processed_files.append({
                    "name": file_name,
                    "type": file_type,
                    "path": file_path,
                })
        
        # 合并上下文
        context = "\\n\\n".join(contexts) if contexts else ""
        
        # 生成完整文本
        full_text = text
        if context:
            full_text = f"{text}\\n\\n{context}" if text else context
        
        return {
            "success": True,
            "text": full_text,
            "context": context,
            "original_text": text,
            "files_processed": processed_files,
            "suggestions": suggestions,
        }
    
    def _analyze_file(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """分析文件内容
        
        Args:
            file_path: 文件路径
            file_type: 文件类型
        
        Returns:
            {
                "success": bool,
                "summary": str,
                "details": dict,
                "suggestions": list,
            }
        """
        try:
            if file_type == "image":
                return self._analyze_image(file_path)
            
            elif file_type == "audio":
                return self._analyze_audio(file_path)
            
            elif file_type == "document":
                return self._analyze_document(file_path)
            
            elif file_type == "data":
                return self._analyze_data(file_path)
            
            elif file_type == "code":
                return self._analyze_code(file_path)
            
            else:
                return {
                    "success": False,
                    "summary": "Unknown file type",
                    "suggestions": [],
                }
        
        except Exception as e:
            logger.error(f"Failed to analyze file {file_path}: {e}")
            return {
                "success": False,
                "summary": f"Error: {str(e)}",
                "suggestions": [],
            }
    
    def _analyze_image(self, file_path: str) -> Dict[str, Any]:
        """分析图像"""
        try:
            from app.tools.tool_registry import ToolRegistry
            
            # 尝试图像分析
            result = ToolRegistry.execute(
                "analyze_image",
                image_path=file_path,
                question="描述这张图片的主要内容",
            )
            
            if result.get("success"):
                return {
                    "success": True,
                    "summary": result.get("description", "图像已加载"),
                    "details": result,
                    "suggestions": [
                        "你可以问我关于这张图片的任何问题",
                        "我也可以帮你识别图片中的文字",
                        "需要的话我可以对比多张图片",
                    ],
                }
            else:
                # 降级：仅记录文件
                return {
                    "success": True,
                    "summary": f"图像文件已加载（{Path(file_path).stat().st_size // 1024}KB）",
                    "suggestions": ["你可以问我关于这张图片的问题"],
                }
        
        except Exception as e:
            return {
                "success": True,
                "summary": f"图像已加载（分析失败: {e}）",
                "suggestions": [],
            }
    
    def _analyze_audio(self, file_path: str) -> Dict[str, Any]:
        """分析音频"""
        try:
            from app.tools.tool_registry import ToolRegistry
            
            # 尝试转录
            result = ToolRegistry.execute(
                "transcribe_audio",
                audio_path=file_path,
                language="auto",
            )
            
            if result.get("success"):
                transcript = result.get("transcript", "")
                
                return {
                    "success": True,
                    "summary": f"音频转录:\\n{transcript[:500]}...",
                    "details": {"transcript": transcript},
                    "suggestions": [
                        "转录完成，你可以让我总结内容",
                        "我可以帮你提取关键信息",
                    ],
                }
            else:
                return {
                    "success": True,
                    "summary": "音频文件已加载",
                    "suggestions": ["需要我转录音频内容吗？"],
                }
        
        except Exception as e:
            return {
                "success": True,
                "summary": f"音频已加载（转录失败: {e}）",
                "suggestions": [],
            }
    
    def _analyze_document(self, file_path: str) -> Dict[str, Any]:
        """分析文档"""
        try:
            from app.tools.tool_registry import ToolRegistry
            
            # 解析文档
            result = ToolRegistry.execute(
                "parse_document",
                file_path=file_path,
            )
            
            if result.get("success"):
                content = result.get("content", "")
                summary = content[:500] + "..." if len(content) > 500 else content
                
                return {
                    "success": True,
                    "summary": summary,
                    "details": {"full_content": content},
                    "suggestions": [
                        "文档已解析，你可以让我总结要点",
                        "我可以帮你提取关键信息",
                        "需要的话我可以回答文档相关问题",
                    ],
                }
            else:
                return {
                    "success": True,
                    "summary": "文档已加载（解析失败）",
                    "suggestions": [],
                }
        
        except Exception as e:
            return {
                "success": True,
                "summary": f"文档已加载（解析失败: {e}）",
                "suggestions": [],
            }
    
    def _analyze_data(self, file_path: str) -> Dict[str, Any]:
        """分析数据文件"""
        try:
            from app.tools.tool_registry import ToolRegistry
            
            # 数据分析
            result = ToolRegistry.execute(
                "analyze_data",
                file_path=file_path,
                analysis_type="summary",
            )
            
            if result.get("success"):
                stats = result.get("statistics", {})
                summary = f"数据统计:\\n行数: {stats.get('rows', 'N/A')}\\n列数: {stats.get('columns', 'N/A')}"
                
                return {
                    "success": True,
                    "summary": summary,
                    "details": result,
                    "suggestions": [
                        "数据已加载，我可以帮你分析",
                        "需要我生成可视化图表吗？",
                        "我可以计算统计数据或查找异常值",
                    ],
                }
            else:
                return {
                    "success": True,
                    "summary": "数据文件已加载",
                    "suggestions": ["需要我分析数据吗？"],
                }
        
        except Exception as e:
            return {
                "success": True,
                "summary": f"数据已加载（分析失败: {e}）",
                "suggestions": [],
            }
    
    def _analyze_code(self, file_path: str) -> Dict[str, Any]:
        """分析代码文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # 简单代码分析
            lines = code.split('\\n')
            imports = [l for l in lines if l.strip().startswith('import ') or l.strip().startswith('from ')]
            functions = [l for l in lines if 'def ' in l or 'function ' in l]
            
            summary = f"代码文件: {len(lines)}行\\n"
            summary += f"导入: {len(imports)}个\\n"
            summary += f"函数: {len(functions)}个"
            
            return {
                "success": True,
                "summary": summary,
                "details": {
                    "lines": len(lines),
                    "imports": imports[:5],
                    "functions": functions[:5],
                },
                "suggestions": [
                    "代码已加载，我可以帮你理解或优化",
                    "需要我解释代码逻辑吗？",
                    "我可以帮你重构或添加注释",
                ],
            }
        
        except Exception as e:
            return {
                "success": True,
                "summary": f"代码已加载（分析失败: {e}）",
                "suggestions": [],
            }
    
    def route_to_tool(self, text: str, files: List[str] = None) -> Dict[str, Any]:
        """智能路由到合适的工具
        
        Args:
            text: 用户文本
            files: 文件列表
        
        Returns:
            {
                "tool": str,
                "parameters": dict,
                "reasoning": str,
            }
        """
        files = files or []
        
        # 无文件时的路由
        if not files:
            return self._route_text_only(text)
        
        # 有文件时的路由
        file_types = [self.detect_type(f) for f in files]
        
        # 单文件路由
        if len(files) == 1:
            file_type = file_types[0]
            file_path = files[0]
            
            if file_type == "image":
                return {
                    "tool": "analyze_image",
                    "parameters": {
                        "image_path": file_path,
                        "question": text,
                    },
                    "reasoning": "图像文件，使用图像分析工具",
                }
            
            elif file_type == "audio":
                return {
                    "tool": "transcribe_audio",
                    "parameters": {
                        "audio_path": file_path,
                        "language": "auto",
                    },
                    "reasoning": "音频文件，使用语音转录工具",
                }
            
            elif file_type == "document":
                return {
                    "tool": "parse_document",
                    "parameters": {"file_path": file_path},
                    "reasoning": "文档文件，使用文档解析工具",
                }
            
            elif file_type == "data":
                return {
                    "tool": "analyze_data",
                    "parameters": {
                        "file_path": file_path,
                        "analysis_type": "summary",
                        "query": text,
                    },
                    "reasoning": "数据文件，使用数据分析工具",
                }
        
        # 多文件或其他情况
        return {
            "tool": "process_multimodal",
            "parameters": {
                "text": text,
                "files": files,
            },
            "reasoning": "多文件输入，使用多模态处理器",
        }
    
    def _route_text_only(self, text: str) -> Dict[str, Any]:
        """纯文本路由"""
        text_lower = text.lower()
        
        # 搜索意图
        if any(kw in text_lower for kw in ["搜索", "查找", "search", "find"]):
            return {
                "tool": "web_search",
                "parameters": {"query": text, "num_results": 5},
                "reasoning": "检测到搜索意图",
            }
        
        # 计算意图
        elif any(kw in text_lower for kw in ["计算", "等于", "calculate", "compute"]):
            return {
                "tool": "calculate",
                "parameters": {"expression": text},
                "reasoning": "检测到计算意图",
            }
        
        # 代码执行意图
        elif any(kw in text_lower for kw in ["运行代码", "执行", "run code", "execute"]):
            return {
                "tool": "execute_code",
                "parameters": {"code": text},
                "reasoning": "检测到代码执行意图",
            }
        
        # 默认：Agent处理
        else:
            return {
                "tool": "agent",
                "parameters": {"task": text},
                "reasoning": "使用Agent处理通用任务",
            }


# 全局实例
_processor = None


def get_multimodal_processor() -> MultimodalInputProcessor:
    """获取全局多模态处理器"""
    global _processor
    if _processor is None:
        _processor = MultimodalInputProcessor()
    return _processor
