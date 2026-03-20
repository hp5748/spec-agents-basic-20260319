"""
Python Adapter 模块

提供本地 Python 代码执行能力，包括：
- 执行器：安全执行 Python 函数
- 沙箱：受限的执行环境
- 加载器：从 skills/ 目录加载技能
"""

from .executor import (
    PythonAdapter,
    PythonFunction,
    get_python_adapter,
    register_python_function,
)
from .sandbox import PythonSandbox, SandboxError, get_sandbox
from .loader import SkillLoader, SkillMetadata, load_skills


__all__ = [
    # 执行器
    "PythonAdapter",
    "PythonFunction",
    "get_python_adapter",
    "register_python_function",
    # 沙箱
    "PythonSandbox",
    "SandboxError",
    "get_sandbox",
    # 加载器
    "SkillLoader",
    "SkillMetadata",
    "load_skills",
]
