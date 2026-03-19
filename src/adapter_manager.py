"""
适配器管理器

连接 Skill 层和 Adapter 层，负责适配器的生命周期管理。

使用方式:
    manager = AdapterManager("config/adapters.yaml")
    await manager.initialize()

    # 获取适配器
    adapter = manager.get_adapter_for_skill(skill_config)

    # 执行
    result = await adapter.execute(context, input_data)
"""

from typing import Any, Dict, List, Optional
import logging
from pathlib import Path

from adapters.core import (
    AdapterType,
    AdapterConfig,
    AdapterResult,
    SkillContext,
    BaseAdapter,
    AdapterFactory,
)
from adapters.core.adapter_factory import register_builtin_adapters


logger = logging.getLogger(__name__)


class AdapterManager:
    """
    适配器管理器

    职责：
    - 加载适配器配置
    - 注册内置适配器
    - 创建和管理适配器实例
    - 连接 Skill 和 Adapter
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化适配器管理器

        Args:
            config_path: 配置文件路径 (config/adapters.yaml)
        """
        self._config_path = config_path
        self._configs: Dict[str, AdapterConfig] = {}
        self._adapters: Dict[str, BaseAdapter] = {}
        self._initialized = False

        # 注册内置适配器
        register_builtin_adapters()

    async def initialize(self) -> bool:
        """
        初始化适配器管理器

        - 加载配置文件
        - 创建适配器实例
        """
        if self._initialized:
            return True

        try:
            # 加载配置
            if self._config_path:
                self._load_config(self._config_path)

            # 初始化所有适配器
            results = await AdapterFactory.initialize_all()
            failed = [k for k, v in results.items() if not v]
            if failed:
                logger.warning(f"部分适配器初始化失败: {failed}")

            self._initialized = True
            logger.info(f"适配器管理器初始化完成，已加载 {len(self._configs)} 个配置")
            return True

        except Exception as e:
            logger.error(f"适配器管理器初始化失败: {e}")
            return False

    def _load_config(self, config_path: str) -> None:
        """
        加载配置文件

        Args:
            config_path: 配置文件路径
        """
        path = Path(config_path)
        if not path.exists():
            logger.warning(f"配置文件不存在: {config_path}")
            return

        try:
            import yaml
            with open(path, encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except ImportError:
            import json
            with open(path, encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return

        # 解析各类型适配器配置
        for adapter_type in [AdapterType.HTTP, AdapterType.MCP, AdapterType.SHELL]:
            type_name = adapter_type.value
            type_configs = config.get(type_name, {})

            for name, cfg in type_configs.items():
                adapter_config = AdapterConfig(
                    type=adapter_type,
                    name=name,
                    enabled=cfg.get("enabled", True),
                    timeout=cfg.get("timeout", config.get("global", {}).get("default_timeout", 30)),
                    metadata=cfg,
                )
                self._configs[name] = adapter_config

                # 如果启用则创建实例
                if adapter_config.enabled:
                    try:
                        AdapterFactory.get_or_create(adapter_config)
                    except Exception as e:
                        logger.error(f"创建适配器失败 {name}: {e}")

    def get_adapter_for_skill(self, skill_config: Dict[str, Any]) -> Optional[BaseAdapter]:
        """
        根据 Skill 配置获取适配器

        Args:
            skill_config: Skill 配置（来自 SKILL.md）

        Returns:
            Optional[BaseAdapter]: 适配器实例
        """
        adapter_config = skill_config.get("adapter", {})
        adapter_type = adapter_config.get("type", "python")

        # Python 类型使用 Skill 内置执行器
        if adapter_type == "python":
            return None

        # 查找已注册的适配器
        adapter_name = adapter_config.get("adapter_name")
        if adapter_name:
            return AdapterFactory.get_instance(adapter_name)

        # 动态创建适配器
        try:
            config = AdapterConfig(
                type=AdapterType(adapter_type),
                name=skill_config.get("name", "dynamic"),
                metadata=adapter_config,
            )
            return AdapterFactory.create(config)
        except Exception as e:
            logger.error(f"获取适配器失败: {e}")
            return None

    def get_adapter(self, name: str) -> Optional[BaseAdapter]:
        """
        获取已注册的适配器

        Args:
            name: 适配器名称

        Returns:
            Optional[BaseAdapter]: 适配器实例
        """
        return AdapterFactory.get_instance(name)

    def list_adapters(self) -> List[str]:
        """获取所有已注册的适配器名称"""
        return list(AdapterFactory._instances.keys())

    def list_available_types(self) -> List[str]:
        """获取所有可用的适配器类型"""
        return AdapterFactory.get_available_types()

    async def health_check_all(self) -> Dict[str, bool]:
        """
        检查所有适配器健康状态

        Returns:
            Dict[str, bool]: 各适配器的健康状态
        """
        results = {}
        for name, adapter in AdapterFactory._instances.items():
            try:
                results[name] = await adapter.health_check()
            except Exception as e:
                logger.error(f"健康检查失败 {name}: {e}")
                results[name] = False
        return results

    async def cleanup(self) -> None:
        """清理所有适配器"""
        await AdapterFactory.cleanup_all()
        self._adapters.clear()
        self._initialized = False
        logger.info("适配器管理器已清理")


# 全局管理器实例
_manager: Optional[AdapterManager] = None


def get_manager() -> AdapterManager:
    """获取全局管理器实例"""
    global _manager
    if _manager is None:
        _manager = AdapterManager()
    return _manager


async def initialize_manager(config_path: Optional[str] = None) -> bool:
    """初始化全局管理器"""
    global _manager
    _manager = AdapterManager(config_path)
    return await _manager.initialize()
