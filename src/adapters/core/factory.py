"""
Adapter 工厂

管理适配器的注册、创建和路由。
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Type

from .base import BaseAdapter, MockAdapter
from .types import (
    AdapterConfig,
    AdapterType,
    ToolRequest,
    ToolResponse
)


logger = logging.getLogger(__name__)


class AdapterFactory:
    """
    适配器工厂

    核心功能：
    1. 注册适配器类
    2. 创建适配器实例
    3. 路由工具调用到正确的适配器
    4. 管理适配器生命周期

    设计模式：
    - 工厂模式：创建适配器实例
    - 注册表模式：管理适配器类型
    - 策略模式：动态选择适配器
    """

    def __init__(self):
        """初始化工厂"""
        # 适配器类型注册表：type -> class
        self._adapter_classes: Dict[AdapterType, Type[BaseAdapter]] = {}

        # 适配器实例注册表：name -> instance
        self._adapters: Dict[str, BaseAdapter] = {}

        # 工具到适配器的映射：tool_name -> adapter_name
        self._tool_mapping: Dict[str, str] = {}

        # 锁
        self._lock = asyncio.Lock()

        # 注册内置适配器
        self._register_builtin_adapters()

    def _register_builtin_adapters(self) -> None:
        """注册内置适配器"""
        self.register_adapter_class(AdapterType.CUSTOM, MockAdapter)

        # 注册 MCP Adapter
        try:
            from ..mcp import MCPAdapter
            self.register_adapter_class(AdapterType.MCP, MCPAdapter)
        except ImportError as e:
            logger.warning(f"MCP Adapter 注册失败: {e}")

    def register_adapter_class(
        self,
        adapter_type: AdapterType,
        adapter_class: Type[BaseAdapter]
    ) -> None:
        """
        注册适配器类

        Args:
            adapter_type: 适配器类型
            adapter_class: 适配器类（必须继承 BaseAdapter）
        """
        if not issubclass(adapter_class, BaseAdapter):
            raise ValueError(f"{adapter_class} must inherit from BaseAdapter")

        self._adapter_classes[adapter_type] = adapter_class
        logger.info(f"已注册适配器类: {adapter_type.value} -> {adapter_class.__name__}")

    async def create_adapter(self, config: AdapterConfig) -> BaseAdapter:
        """
        创建适配器实例

        Args:
            config: 适配器配置

        Returns:
            BaseAdapter: 适配器实例

        Raises:
            ValueError: 不支持的适配器类型
        """
        adapter_class = self._adapter_classes.get(config.type)

        if not adapter_class:
            raise ValueError(f"不支持的适配器类型: {config.type.value}")

        # 创建实例
        adapter = adapter_class(config)

        # 初始化
        await adapter.initialize()

        # 注册实例
        async with self._lock:
            self._adapters[config.name] = adapter

            # 更新工具映射
            capabilities = adapter.get_capabilities()
            for tool_name in capabilities.tools:
                self._tool_mapping[tool_name] = config.name

        logger.info(f"已创建适配器实例: {config.name} (类型: {config.type.value})")
        return adapter

    async def get_adapter(self, adapter_name: str) -> Optional[BaseAdapter]:
        """
        获取适配器实例

        Args:
            adapter_name: 适配器名称

        Returns:
            Optional[BaseAdapter]: 适配器实例，不存在返回 None
        """
        return self._adapters.get(adapter_name)

    async def route(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        **kwargs
    ) -> ToolResponse:
        """
        路由工具调用到正确的适配器

        Args:
            tool_name: 工具名称
            parameters: 工具参数
            **kwargs: 其他请求参数

        Returns:
            ToolResponse: 执行响应
        """
        # 查找适配器
        adapter_name = self._tool_mapping.get(tool_name)

        if not adapter_name:
            return ToolResponse.from_error(f"工具未注册: {tool_name}", tool_name)

        adapter = self._adapters.get(adapter_name)

        if not adapter:
            return ToolResponse.from_error(f"适配器不存在: {adapter_name}", tool_name)

        if not adapter.is_enabled():
            return ToolResponse.from_error(f"适配器已禁用: {adapter_name}", tool_name)

        # 构建请求
        request = ToolRequest(
            tool_name=tool_name,
            parameters=parameters,
            **kwargs
        )

        # 执行
        return await adapter.execute(request)

    async def route_to_adapter(
        self,
        adapter_name: str,
        tool_name: str,
        parameters: Dict[str, Any],
        **kwargs
    ) -> ToolResponse:
        """
        路由到指定适配器

        Args:
            adapter_name: 适配器名称
            tool_name: 工具名称
            parameters: 工具参数
            **kwargs: 其他请求参数

        Returns:
            ToolResponse: 执行响应
        """
        adapter = self._adapters.get(adapter_name)

        if not adapter:
            return ToolResponse.from_error(f"适配器不存在: {adapter_name}", tool_name)

        if not adapter.is_enabled():
            return ToolResponse.from_error(f"适配器已禁用: {adapter_name}", tool_name)

        request = ToolRequest(
            tool_name=tool_name,
            parameters=parameters,
            **kwargs
        )

        return await adapter.execute(request)

    def list_adapters(
        self,
        adapter_type: Optional[AdapterType] = None,
        enabled_only: bool = True
    ) -> List[BaseAdapter]:
        """
        列出适配器

        Args:
            adapter_type: 适配器类型过滤
            enabled_only: 是否只返回启用的适配器

        Returns:
            List[BaseAdapter]: 适配器列表
        """
        adapters = []

        for adapter in self._adapters.values():
            if adapter_type and adapter.config.type != adapter_type:
                continue

            if enabled_only and not adapter.is_enabled():
                continue

            adapters.append(adapter)

        return adapters

    def list_adapter_names(
        self,
        adapter_type: Optional[AdapterType] = None,
        enabled_only: bool = True
    ) -> List[str]:
        """
        列出适配器名称

        Args:
            adapter_type: 适配器类型过滤
            enabled_only: 是否只返回启用的适配器

        Returns:
            List[str]: 适配器名称列表
        """
        adapters = self.list_adapters(adapter_type, enabled_only)
        return [adapter.config.name for adapter in adapters]

    def list_tools(
        self,
        adapter_name: Optional[str] = None
    ) -> List[str]:
        """
        列出工具

        Args:
            adapter_name: 适配器名称（None 表示全部）

        Returns:
            List[str]: 工具名称列表
        """
        if adapter_name:
            adapter = self._adapters.get(adapter_name)
            if not adapter:
                return []
            return adapter.get_capabilities().tools
        else:
            return list(self._tool_mapping.keys())

    async def remove_adapter(self, adapter_name: str) -> bool:
        """
        移除适配器

        Args:
            adapter_name: 适配器名称

        Returns:
            bool: 是否成功
        """
        adapter = self._adapters.get(adapter_name)

        if not adapter:
            return False

        # 关闭适配器
        await adapter.shutdown()

        # 移除工具映射
        capabilities = adapter.get_capabilities()
        for tool_name in capabilities.tools:
            if self._tool_mapping.get(tool_name) == adapter_name:
                del self._tool_mapping[tool_name]

        # 移除实例
        async with self._lock:
            del self._adapters[adapter_name]

        logger.info(f"已移除适配器: {adapter_name}")
        return True

    async def health_check(
        self,
        adapter_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        健康检查

        Args:
            adapter_name: 适配器名称（None 表示全部）

        Returns:
            Dict: 健康状态
        """
        if adapter_name:
            adapter = self._adapters.get(adapter_name)
            if not adapter:
                return {"adapter_name": adapter_name, "status": "not_found"}

            status = await adapter.health_check()
            return {
                "adapter_name": adapter_name,
                "status": status.to_dict()
            }

        # 检查所有适配器
        results = {}
        for name, adapter in self._adapters.items():
            status = await adapter.health_check()
            results[name] = status.to_dict()

        return results

    async def shutdown_all(self) -> None:
        """关闭所有适配器"""
        shutdown_tasks = []

        for adapter in self._adapters.values():
            shutdown_tasks.append(adapter.shutdown())

        if shutdown_tasks:
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)

        self._adapters.clear()
        self._tool_mapping.clear()

        logger.info("所有适配器已关闭")

    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            Dict: 统计数据
        """
        stats = {
            "total_adapters": len(self._adapters),
            "total_tools": len(self._tool_mapping),
            "by_type": {}
        }

        for adapter in self._adapters.values():
            adapter_type = adapter.config.type.value
            if adapter_type not in stats["by_type"]:
                stats["by_type"][adapter_type] = 0
            stats["by_type"][adapter_type] += 1

        return stats


# 全局单例
_global_factory: Optional[AdapterFactory] = None


def get_global_factory() -> AdapterFactory:
    """
    获取全局工厂实例

    Returns:
        AdapterFactory: 全局工厂
    """
    global _global_factory
    if _global_factory is None:
        _global_factory = AdapterFactory()
    return _global_factory


def reset_global_factory() -> None:
    """重置全局工厂（主要用于测试）"""
    global _global_factory
    _global_factory = None
