"""
Adapters 模块

统一适配器架构，支持 Skills、MCP、SubAgent 等多种工具执行方式。

架构设计：
- core/: 核心框架（基类、工厂、类型）
- skill/: Skill 适配器
- mcp/: MCP 适配器
- subagent/: SubAgent 适配器
- custom/: 自定义适配器

使用方式：
    from src.adapters import AdapterFactory, get_global_factory

    factory = get_global_factory()

    # 路由工具调用
    response = await factory.route("tool_name", {"param": "value"})
"""

from .core import (
    AdapterFactory,
    AdapterType,
    BaseAdapter,
    MockAdapter,
    ToolRequest,
    ToolResponse,
    get_global_factory,
    reset_global_factory
)

__all__ = [
    "AdapterFactory",
    "AdapterType",
    "BaseAdapter",
    "MockAdapter",
    "ToolRequest",
    "ToolResponse",
    "get_global_factory",
    "reset_global_factory",
]
