"""
Adapter 核心模块

提供统一的适配器架构，支持多种工具执行方式。

核心组件：
- BaseAdapter: 适配器基类
- AdapterFactory: 适配器工厂
- 类型定义：AdapterType, AdapterConfig, ToolRequest, ToolResponse 等

使用方式：
    from src.adapters.core import BaseAdapter, AdapterFactory, AdapterConfig, AdapterType

    # 创建自定义适配器
    class MyAdapter(BaseAdapter):
        async def initialize(self):
            pass

        async def execute(self, request):
            return ToolResponse.from_success("Hello")

    # 注册并使用
    factory = AdapterFactory()
    factory.register_adapter_class(AdapterType.CUSTOM, MyAdapter)

    config = AdapterConfig(type=AdapterType.CUSTOM, name="my_adapter")
    adapter = await factory.create_adapter(config)

    # 执行工具
    response = await factory.route("my_tool", {"param": "value"})
"""

from .base import BaseAdapter, MockAdapter
from .factory import AdapterFactory, get_global_factory, reset_global_factory
from .types import (
    AdapterCapabilities,
    AdapterConfig,
    AdapterHealthStatus,
    AdapterType,
    ToolRequest,
    ToolResponse
)

__all__ = [
    # 基类
    "BaseAdapter",
    "MockAdapter",

    # 工厂
    "AdapterFactory",
    "get_global_factory",
    "reset_global_factory",

    # 类型
    "AdapterType",
    "AdapterConfig",
    "ToolRequest",
    "ToolResponse",
    "AdapterHealthStatus",
    "AdapterCapabilities",
]
