"""
Python 沙箱执行环境

提供受限的 Python 执行环境，限制：
- 可访问的模块
- 执行时间
- 资源使用
"""

import asyncio
import logging
import sys
from typing import Any, Dict, Optional, Set


logger = logging.getLogger(__name__)


# 默认允许的模块
DEFAULT_ALLOWED_MODULES: Set[str] = {
    "json",
    "datetime",
    "math",
    "re",
    "typing",
    "dataclasses",
    "collections",
    "itertools",
    "functools",
}


class SandboxError(Exception):
    """沙箱执行错误"""
    pass


class PythonSandbox:
    """
    Python 沙箱执行环境

    提供受限的执行环境，限制可访问的模块和资源。
    注意：这是一个基础实现，生产环境应使用更专业的方案如 RestrictedPython。
    """

    def __init__(
        self,
        allowed_modules: Optional[Set[str]] = None,
        timeout: float = 30.0,
        max_memory_mb: int = 100,
    ):
        self.allowed_modules = allowed_modules or DEFAULT_ALLOWED_MODULES.copy()
        self.timeout = timeout
        self.max_memory_mb = max_memory_mb
        self._original_modules: Dict[str, Any] = {}

    def _restrict_imports(self) -> None:
        """限制导入"""
        # 保存原始的 __import__
        self._original_modules["__import__"] = __builtins__.__import__

        def restricted_import(name: str, *args, **kwargs):
            # 检查模块是否在允许列表中
            for allowed in self.allowed_modules:
                if name == allowed or name.startswith(allowed + "."):
                    return self._original_modules["__import__"](name, *args, **kwargs)

            raise ImportError(f"模块 '{name}' 不在允许的导入列表中")

        __builtins__.__import__ = restricted_import

    def _restore_imports(self) -> None:
        """恢复导入"""
        if "__import__" in self._original_modules:
            __builtins__.__import__ = self._original_modules["__import__"]

    async def execute_code(self, code: str, globals_dict: Optional[Dict] = None) -> Any:
        """
        执行沙箱代码

        Args:
            code: 要执行的代码
            globals_dict: 全局变量字典

        Returns:
            执行结果
        """
        self._restrict_imports()

        try:
            # 在超时内执行
            result = await asyncio.wait_for(
                self._execute(code, globals_dict or {}),
                timeout=self.timeout,
            )
            return result

        except asyncio.TimeoutError:
            raise SandboxError(f"代码执行超过 {self.timeout} 秒超时")
        except Exception as e:
            raise SandboxError(f"沙箱执行错误: {e}")
        finally:
            self._restore_imports()

    async def _execute(self, code: str, globals_dict: Dict) -> Any:
        """实际执行代码"""
        # 创建受限的全局命名空间
        restricted_globals = {
            "__builtins__": {
                "print": print,
                "len": len,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "list": list,
                "dict": dict,
                "tuple": tuple,
                "set": set,
                "range": range,
                "enumerate": enumerate,
                "zip": zip,
            }
        }
        restricted_globals.update(globals_dict)

        # 执行代码
        exec(code, restricted_globals)

        # 尝试获取结果
        return restricted_globals.get("_result")

    def is_safe_code(self, code: str) -> bool:
        """
        基本的安全检查

        检查代码是否包含潜在危险的字符串。
        注意：这不是安全保证，只是基础检查。
        """
        dangerous_patterns = [
            "import os",
            "import sys",
            "import subprocess",
            "import shutil",
            "__import__",
            "eval(",
            "exec(",
            "compile(",
            "open(",
            "file(",
            "__class__",
            "__bases__",
            "__subclasses__",
            "__globals__",
            "__code__",
            "__closure__",
        ]

        code_lower = code.lower()
        for pattern in dangerous_patterns:
            if pattern in code_lower:
                logger.warning(f"代码包含潜在危险模式: {pattern}")
                return False

        return True


# 全局沙箱实例
_global_sandbox: Optional[PythonSandbox] = None


def get_sandbox() -> PythonSandbox:
    """获取全局沙箱实例"""
    global _global_sandbox
    if _global_sandbox is None:
        _global_sandbox = PythonSandbox()
    return _global_sandbox
