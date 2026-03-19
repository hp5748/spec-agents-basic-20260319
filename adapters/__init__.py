"""
Adapters - 通用适配器模块

支持多种类型的 Skill 执行方式：
- Python: 执行 Skill 内置脚本
- HTTP: 调用 REST API (OpenAPI 3.0)
- MCP: 连接 MCP Server (Model Context Protocol)
- Shell: 执行命令行工具

参考项目：
- alirezarezvani/claude-skills (192+ Skills)
- modelcontextprotocol/servers (官方 MCP)
- encode/httpx (HTTP 客户端)
"""

from .core.types import (
    AdapterType,
    AdapterConfig,
    AdapterResult,
    SkillContext,
    ExecutionStatus,
)
from .core.base_adapter import BaseAdapter
from .core.adapter_factory import AdapterFactory

__all__ = [
    # 类型
    "AdapterType",
    "AdapterConfig",
    "AdapterResult",
    "SkillContext",
    "ExecutionStatus",
    # 基类
    "BaseAdapter",
    # 工厂
    "AdapterFactory",
]

__version__ = "1.0.0"
