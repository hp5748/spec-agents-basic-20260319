"""
Shell 适配器模块

支持执行命令行工具，提供沙箱安全机制。

特性：
- 命令白名单/黑名单
- 危险命令检测（正则模式）
- 资源限制（CPU、内存、时间）
- 超时控制
- 输出捕获
- 并发控制
- 批量执行

参考项目：
- faif/python-patterns
- Docker 容器安全
"""

from .base import ShellAdapter
from .sandbox import (
    SandboxConfig,
    SandboxValidator,
    DEFAULT_ALLOWED_COMMANDS,
    DEFAULT_BLOCKED_COMMANDS,
    DANGEROUS_PATTERNS,
    create_sandbox_validator,
)
from .executor import (
    ExecutionConfig,
    ExecutionResult,
    ShellExecutor,
    create_executor,
)


__all__ = [
    # 适配器
    "ShellAdapter",
    # 沙箱
    "SandboxConfig",
    "SandboxValidator",
    "DEFAULT_ALLOWED_COMMANDS",
    "DEFAULT_BLOCKED_COMMANDS",
    "DANGEROUS_PATTERNS",
    "create_sandbox_validator",
    # 执行器
    "ExecutionConfig",
    "ExecutionResult",
    "ShellExecutor",
    "create_executor",
]
