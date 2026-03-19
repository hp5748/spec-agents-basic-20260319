"""
适配器工厂

负责注册、创建和管理适配器实例。

参考：
- 工厂模式 (faif/python-patterns)
"""

from typing import Dict, List, Optional, Type
import logging

from .types import AdapterType, AdapterConfig
from .base_adapter import BaseAdapter


logger = logging.getLogger(__name__)


class AdapterFactory:
    """
    适配器工厂

    负责适配器的注册和创建。使用类方法实现全局注册表。

    使用方式:
        # 注册适配器
        AdapterFactory.register(AdapterType.HTTP, HTTPAdapter)

        # 创建适配器实例
        config = AdapterConfig(type=AdapterType.HTTP, name="order-api")
        adapter = AdapterFactory.create(config)

        # 获取可用类型
        types = AdapterFactory.get_available_types()
    """

    _registry: Dict[AdapterType, Type[BaseAdapter]] = {}
    _instances: Dict[str, BaseAdapter] = {}

    @classmethod
    def register(
        cls,
        adapter_type: AdapterType,
        adapter_class: Type[BaseAdapter]
    ) -> None:
        """
        注册适配器类

        Args:
            adapter_type: 适配器类型
            adapter_class: 适配器类（必须继承 BaseAdapter）

        Raises:
            TypeError: 如果 adapter_class 不是 BaseAdapter 的子类
        """
        if not issubclass(adapter_class, BaseAdapter):
            raise TypeError(
                f"适配器类必须继承 BaseAdapter: {adapter_class}"
            )

        cls._registry[adapter_type] = adapter_class
        logger.info(f"注册适配器: {adapter_type.value} -> {adapter_class.__name__}")

    @classmethod
    def create(cls, config: AdapterConfig) -> BaseAdapter:
        """
        创建适配器实例

        Args:
            config: 适配器配置

        Returns:
            BaseAdapter: 适配器实例

        Raises:
            ValueError: 如果适配器类型未注册
        """
        adapter_class = cls._registry.get(config.type)
        if not adapter_class:
            raise ValueError(f"未注册的适配器类型: {config.type.value}")

        adapter = adapter_class(config)
        logger.debug(f"创建适配器实例: {config.name} ({config.type.value})")
        return adapter

    @classmethod
    def get_or_create(cls, config: AdapterConfig) -> BaseAdapter:
        """
        获取或创建适配器实例（单例模式）

        如果已存在同名实例则返回现有实例，否则创建新实例。

        Args:
            config: 适配器配置

        Returns:
            BaseAdapter: 适配器实例
        """
        if config.name in cls._instances:
            return cls._instances[config.name]

        adapter = cls.create(config)
        cls._instances[config.name] = adapter
        return adapter

    @classmethod
    def get_instance(cls, name: str) -> Optional[BaseAdapter]:
        """
        获取已创建的适配器实例

        Args:
            name: 适配器名称

        Returns:
            Optional[BaseAdapter]: 适配器实例，如果不存在返回 None
        """
        return cls._instances.get(name)

    @classmethod
    def remove_instance(cls, name: str) -> bool:
        """
        移除适配器实例

        Args:
            name: 适配器名称

        Returns:
            bool: 是否成功移除
        """
        if name in cls._instances:
            del cls._instances[name]
            logger.info(f"移除适配器实例: {name}")
            return True
        return False

    @classmethod
    def get_available_types(cls) -> List[str]:
        """
        获取所有已注册的适配器类型

        Returns:
            List[str]: 适配器类型列表
        """
        return [t.value for t in cls._registry.keys()]

    @classmethod
    def is_registered(cls, adapter_type: AdapterType) -> bool:
        """
        检查适配器类型是否已注册

        Args:
            adapter_type: 适配器类型

        Returns:
            bool: 是否已注册
        """
        return adapter_type in cls._registry

    @classmethod
    def clear_registry(cls) -> None:
        """清空注册表（主要用于测试）"""
        cls._registry.clear()
        cls._instances.clear()

    @classmethod
    async def initialize_all(cls) -> Dict[str, bool]:
        """
        初始化所有已创建的适配器实例

        Returns:
            Dict[str, bool]: 各适配器的初始化结果
        """
        results = {}
        for name, adapter in cls._instances.items():
            try:
                results[name] = await adapter.initialize()
            except Exception as e:
                logger.error(f"初始化适配器失败 {name}: {e}")
                results[name] = False
        return results

    @classmethod
    async def cleanup_all(cls) -> None:
        """清理所有适配器实例"""
        for name, adapter in cls._instances.items():
            try:
                await adapter.cleanup()
            except Exception as e:
                logger.error(f"清理适配器失败 {name}: {e}")
        cls._instances.clear()


def register_builtin_adapters() -> None:
    """
    注册内置适配器

    包括：
    - PythonAdapter: Python 执行器
    - HTTPAdapter: HTTP REST API
    - MCPAdapter: Model Context Protocol
    - ShellAdapter: Shell 命令
    """
    # 注册 Python 适配器（内置在 base_adapter.py）
    from .base_adapter import PythonAdapter
    AdapterFactory.register(AdapterType.PYTHON, PythonAdapter)

    # 注册 HTTP 适配器（延迟加载）
    try:
        from adapters.http import HTTPAdapter
        AdapterFactory.register(AdapterType.HTTP, HTTPAdapter)
    except ImportError:
        logger.debug("HTTP 适配器未安装")

    # 注册 MCP 适配器（延迟加载）
    try:
        from adapters.mcp import MCPAdapter
        AdapterFactory.register(AdapterType.MCP, MCPAdapter)
    except ImportError:
        logger.debug("MCP 适配器未安装")

    # 注册 Shell 适配器（延迟加载）
    try:
        from adapters.shell import ShellAdapter
        AdapterFactory.register(AdapterType.SHELL, ShellAdapter)
    except ImportError:
        logger.debug("Shell 适配器未安装")

    logger.info(f"内置适配器注册完成: {AdapterFactory.get_available_types()}")
