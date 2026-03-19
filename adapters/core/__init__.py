"""
Adapters Core - 核心类型和基类
"""

from .types import (
    AdapterType,
    AdapterConfig,
    AdapterResult,
    SkillContext,
    ExecutionStatus,
)
from .base_adapter import BaseAdapter
from .adapter_factory import AdapterFactory

__all__ = [
    "AdapterType",
    "AdapterConfig",
    "AdapterResult",
    "SkillContext",
    "ExecutionStatus",
    "BaseAdapter",
    "AdapterFactory",
]
