"""插件系统 - 动态加载/卸载技能模块"""
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
import json
import logging
import importlib.util
import sys

logger = logging.getLogger(__name__)

PLUGINS_DIR = Path("E:/AgentProject/plugins")


class Plugin:
    """插件基类"""
    
    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.enabled = False
        self.tools = []
        self.prompts = {}
        self.hooks = {}
    
    def on_load(self):
        """插件加载时调用"""
        pass
    
    def on_unload(self):
        """插件卸载时调用"""
        pass
    
    def register_tool(self, name: str, func: Callable, description: str):
        """注册工具"""
        self.tools.append({
            "name": name,
            "function": func,
            "description": description,
        })
    
    def register_prompt(self, name: str, prompt: str):
        """注册提示词"""
        self.prompts[name] = prompt
    
    def register_hook(self, event: str, callback: Callable):
        """注册事件钩子
        
        Events:
            - on_task_start
            - on_task_end
            - on_tool_call
            - on_error
        """
        if event not in self.hooks:
            self.hooks[event] = []
        self.hooks[event].append(callback)


class PluginManager:
    """插件管理器"""
    
    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}
        self.plugin_configs: Dict[str, Dict] = {}
        self._ensure_plugin_dir()
        self._load_plugin_configs()
    
    def _ensure_plugin_dir(self):
        """确保插件目录存在"""
        PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
        
        # 创建示例插件
        example_dir = PLUGINS_DIR / "example_skill"
        example_dir.mkdir(exist_ok=True)
        
        example_plugin = example_dir / "plugin.py"
        if not example_plugin.exists():
            example_plugin.write_text('''"""示例技能插件"""
from app.agents.plugins import Plugin


class ExampleSkill(Plugin):
    """示例技能：自动问候"""
    
    def __init__(self):
        super().__init__(
            name="example_skill",
            version="1.0.0",
        )
        self.description = "示例插件，展示如何创建技能"
    
    def on_load(self):
        """加载时注册工具"""
        def greet_user(name: str) -> str:
            """问候用户"""
            return f"你好，{name}！我是AI助手。"
        
        self.register_tool(
            name="greet_user",
            func=greet_user,
            description="问候用户",
        )
        
        # 注册提示词
        self.register_prompt(
            name="friendly_response",
            prompt="请用友好的语气回复用户。",
        )
        
        # 注册钩子
        def log_task(task):
            logger.info(f"[Plugin] Task started: {task[:50]}")
        
        self.register_hook("on_task_start", log_task)
    
    def on_unload(self):
        """卸载时清理"""
        logger.info(f"Plugin {self.name} unloaded")


# 插件元数据
PLUGIN_INFO = {
    "name": "example_skill",
    "version": "1.0.0",
    "description": "示例插件",
    "author": "AI Agent",
    "enabled": True,
}
''', encoding='utf-8')
        
        # 创建manifest
        manifest = example_dir / "manifest.json"
        if not manifest.exists():
            manifest.write_text(json.dumps({
                "name": "example_skill",
                "version": "1.0.0",
                "description": "示例技能插件",
                "author": "AI Agent",
                "enabled": True,
                "tools": ["greet_user"],
                "hooks": ["on_task_start"],
            }, indent=2, ensure_ascii=False), encoding='utf-8')
    
    def _load_plugin_configs(self):
        """加载所有插件配置"""
        for plugin_dir in PLUGINS_DIR.iterdir():
            if plugin_dir.is_dir():
                manifest_path = plugin_dir / "manifest.json"
                if manifest_path.exists():
                    try:
                        with open(manifest_path, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                            self.plugin_configs[config["name"]] = config
                            logger.info(f"Found plugin: {config['name']} v{config['version']}")
                    except Exception as e:
                        logger.error(f"Failed to load manifest for {plugin_dir.name}: {e}")
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        """列出所有插件"""
        plugins = []
        
        for name, config in self.plugin_configs.items():
            plugins.append({
                "name": name,
                "version": config.get("version", "unknown"),
                "description": config.get("description", ""),
                "author": config.get("author", "unknown"),
                "enabled": name in self.plugins,
                "tools": config.get("tools", []),
            })
        
        return plugins
    
    def load_plugin(self, name: str) -> Dict[str, Any]:
        """加载插件
        
        Args:
            name: 插件名称
        
        Returns:
            {
                "success": bool,
                "plugin": dict,
                "tools_registered": list,
                "message": str,
            }
        """
        if name in self.plugins:
            return {
                "success": True,
                "plugin": self.plugins[name].__dict__,
                "tools_registered": [],
                "message": f"Plugin {name} already loaded",
            }
        
        plugin_dir = PLUGINS_DIR / name
        if not plugin_dir.exists():
            return {
                "success": False,
                "error": f"Plugin {name} not found",
            }
        
        try:
            # 动态导入插件模块
            plugin_path = plugin_dir / "plugin.py"
            spec = importlib.util.spec_from_file_location(name, plugin_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
            
            # 查找Plugin类
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, Plugin) and attr != Plugin:
                    plugin_class = attr
                    break
            
            if not plugin_class:
                return {
                    "success": False,
                    "error": f"No Plugin class found in {name}",
                }
            
            # 实例化并加载
            plugin = plugin_class()
            plugin.on_load()
            plugin.enabled = True
            
            self.plugins[name] = plugin
            
            # 注册工具到全局ToolRegistry
            tools_registered = []
            if plugin.tools:
                from app.tools.tool_registry import ToolRegistry
                
                for tool_info in plugin.tools:
                    ToolRegistry.register(
                        name=tool_info["name"],
                        function=tool_info["function"],
                        description=tool_info["description"],
                    )
                    tools_registered.append(tool_info["name"])
            
            logger.info(f"Plugin {name} loaded successfully, {len(tools_registered)} tools registered")
            
            return {
                "success": True,
                "plugin": {
                    "name": plugin.name,
                    "version": plugin.version,
                    "tools": len(plugin.tools),
                    "prompts": len(plugin.prompts),
                    "hooks": len(plugin.hooks),
                },
                "tools_registered": tools_registered,
                "message": f"Plugin {name} loaded successfully",
            }
        
        except Exception as e:
            logger.error(f"Failed to load plugin {name}: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    def unload_plugin(self, name: str) -> Dict[str, Any]:
        """卸载插件"""
        if name not in self.plugins:
            return {
                "success": False,
                "error": f"Plugin {name} not loaded",
            }
        
        try:
            plugin = self.plugins[name]
            
            # 调用卸载钩子
            plugin.on_unload()
            
            # 从ToolRegistry移除工具
            if plugin.tools:
                from app.tools.tool_registry import ToolRegistry
                
                for tool_info in plugin.tools:
                    # ToolRegistry不支持注销，标记为禁用
                    pass
            
            # 移除插件
            del self.plugins[name]
            
            # 清理模块
            if name in sys.modules:
                del sys.modules[name]
            
            logger.info(f"Plugin {name} unloaded")
            
            return {
                "success": True,
                "message": f"Plugin {name} unloaded",
            }
        
        except Exception as e:
            logger.error(f"Failed to unload plugin {name}: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    def reload_plugin(self, name: str) -> Dict[str, Any]:
        """重新加载插件"""
        if name in self.plugins:
            unload_result = self.unload_plugin(name)
            if not unload_result["success"]:
                return unload_result
        
        return self.load_plugin(name)
    
    def trigger_hook(self, event: str, *args, **kwargs):
        """触发事件钩子
        
        Args:
            event: 事件名称
            *args, **kwargs: 传递给钩子的参数
        """
        for plugin in self.plugins.values():
            if event in plugin.hooks:
                for callback in plugin.hooks[event]:
                    try:
                        callback(*args, **kwargs)
                    except Exception as e:
                        logger.error(f"Hook {event} in {plugin.name} failed: {e}")
    
    def get_prompt(self, plugin_name: str, prompt_name: str) -> Optional[str]:
        """获取插件提示词"""
        if plugin_name in self.plugins:
            return self.plugins[plugin_name].prompts.get(prompt_name)
        return None
    
    def install_from_zip(self, zip_path: str) -> Dict[str, Any]:
        """从ZIP安装插件"""
        try:
            import zipfile
            import shutil
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # 检查结构
                file_list = zip_ref.namelist()
                
                # 提取插件名称
                plugin_name = Path(zip_path).stem
                
                # 解压到临时目录
                temp_dir = PLUGINS_DIR / f"_temp_{plugin_name}"
                zip_ref.extractall(temp_dir)
                
                # 检查必要文件
                plugin_file = None
                manifest_file = None
                
                for f in temp_dir.rglob("*"):
                    if f.name == "plugin.py":
                        plugin_file = f
                    elif f.name == "manifest.json":
                        manifest_file = f
                
                if not plugin_file or not manifest_file:
                    shutil.rmtree(temp_dir)
                    return {
                        "success": False,
                        "error": "Invalid plugin structure (missing plugin.py or manifest.json)",
                    }
                
                # 移动到正式目录
                target_dir = PLUGINS_DIR / plugin_name
                if target_dir.exists():
                    shutil.rmtree(target_dir)
                
                # 移动文件
                plugin_dir = plugin_file.parent
                shutil.move(str(plugin_dir), str(target_dir))
                
                # 清理临时目录
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                
                # 重新加载配置
                self._load_plugin_configs()
                
                return {
                    "success": True,
                    "message": f"Plugin {plugin_name} installed successfully",
                    "plugin_dir": str(target_dir),
                }
        
        except Exception as e:
            logger.error(f"Failed to install plugin from {zip_path}: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    def create_plugin_template(self, name: str, description: str = "") -> Dict[str, Any]:
        """创建插件模板"""
        try:
            plugin_dir = PLUGINS_DIR / name
            plugin_dir.mkdir(exist_ok=True)
            
            # 创建plugin.py
            plugin_code = f'''"""{description}"""
from app.agents.plugins import Plugin


class {name.capitalize().replace("_", "")}Plugin(Plugin):
    """{description}"""
    
    def __init__(self):
        super().__init__(
            name="{name}",
            version="1.0.0",
        )
        self.description = "{description}"
    
    def on_load(self):
        """加载插件"""
        # TODO: 注册工具
        
        # def my_tool(param: str) -> str:
        #     """工具描述"""
        #     return "result"
        # 
        # self.register_tool("my_tool", my_tool, "工具描述")
        
        pass
    
    def on_unload(self):
        """卸载插件"""
        pass


PLUGIN_INFO = {{
    "name": "{name}",
    "version": "1.0.0",
    "description": "{description}",
    "author": "User",
    "enabled": True,
}}
'''
            (plugin_dir / "plugin.py").write_text(plugin_code, encoding='utf-8')
            
            # 创建manifest.json
            manifest = {
                "name": name,
                "version": "1.0.0",
                "description": description,
                "author": "User",
                "enabled": True,
                "tools": [],
                "hooks": [],
            }
            (plugin_dir / "manifest.json").write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False),
                encoding='utf-8',
            )
            
            # 创建README
            readme = f"""# {name}

{description}

## 功能

- TODO: 添加功能描述

## 使用

```python
# 加载插件
from app.agents.plugins import get_plugin_manager

pm = get_plugin_manager()
pm.load_plugin("{name}")
```

## 工具

- TODO: 列出工具

## 开发

编辑 `plugin.py` 文件来扩展功能。
"""
            (plugin_dir / "README.md").write_text(readme, encoding='utf-8')
            
            # 更新配置
            self.plugin_configs[name] = manifest
            
            return {
                "success": True,
                "message": f"Plugin template created: {name}",
                "plugin_dir": str(plugin_dir),
            }
        
        except Exception as e:
            logger.error(f"Failed to create plugin template: {e}")
            return {
                "success": False,
                "error": str(e),
            }


# 全局实例
_plugin_manager = None


def get_plugin_manager() -> PluginManager:
    """获取全局插件管理器"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager
