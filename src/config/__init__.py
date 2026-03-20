"""
配置模块

提供配置加载和迁移功能：
- loader: 多格式配置加载
- migrator: 配置迁移工具
"""

from .loader import (
    ConfigLoader,
    ConfigFormat,
    ConfigSource,
    get_config_loader,
    load_all_configs,
)
from .migrator import (
    ConfigMigrator,
    migrate_configs,
    should_migrate,
)


__all__ = [
    # 加载器
    "ConfigLoader",
    "ConfigFormat",
    "ConfigSource",
    "get_config_loader",
    "load_all_configs",
    # 迁移器
    "ConfigMigrator",
    "migrate_configs",
    "should_migrate",
]
