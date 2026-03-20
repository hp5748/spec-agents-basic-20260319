"""
Adapter 类型定义

定义适配器系统的核心数据类型。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AdapterType(Enum):
    """适配器类型枚举"""
    SKILL = "skill"           # Skill 适配器
    MCP = "mcp"              # MCP 适配器
    SUBAGENT = "subagent"    # SubAgent 适配器
    CUSTOM = "custom"        # 自定义适配器


@dataclass
class AdapterConfig:
    """
    适配器配置

    所有适配器的通用配置基类
    """
    type: AdapterType         # 适配器类型
    name: str                 # 适配器名称（唯一标识）
    enabled: bool = True      # 是否启用
    timeout: int = 30         # 超时时间（秒）
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "type": self.type.value,
            "name": self.name,
            "enabled": self.enabled,
            "timeout": self.timeout,
            "metadata": self.metadata
        }


@dataclass
class ToolRequest:
    """
    工具调用请求

    统一的工具调用请求格式
    """
    tool_name: str                    # 工具名称
    parameters: Dict[str, Any] = field(default_factory=dict)  # 工具参数

    # 上下文信息
    session_id: str = ""              # 会话ID
    user_input: str = ""              # 用户原始输入
    intent: str = ""                  # 意图

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "session_id": self.session_id,
            "user_input": self.user_input,
            "intent": self.intent,
            "metadata": self.metadata
        }


@dataclass
class ToolResponse:
    """
    工具调用响应

    统一的工具调用响应格式
    """
    success: bool                     # 执行是否成功
    data: Any = None                  # 返回数据
    error: Optional[str] = None       # 错误信息

    # 元数据
    adapter_type: str = ""            # 适配器类型
    tool_name: str = ""               # 工具名称
    execution_time: float = 0.0       # 执行时间（秒）
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 调用链追踪
    source_type: str = "adapter"      # 来源类型
    source_name: str = ""             # 来源名称
    chain_info: List[str] = field(default_factory=list)  # 调用链

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "adapter_type": self.adapter_type,
            "tool_name": self.tool_name,
            "execution_time": self.execution_time,
            "metadata": self.metadata,
            "source_type": self.source_type,
            "source_name": self.source_name,
            "chain_info": self.chain_info
        }

    @classmethod
    def from_error(cls, error: str, tool_name: str = "") -> "ToolResponse":
        """从错误创建响应"""
        return cls(
            success=False,
            error=error,
            tool_name=tool_name
        )

    @classmethod
    def from_success(cls, data: Any, tool_name: str = "") -> "ToolResponse":
        """从成功数据创建响应"""
        return cls(
            success=True,
            data=data,
            tool_name=tool_name
        )


@dataclass
class AdapterHealthStatus:
    """
    适配器健康状态
    """
    healthy: bool                     # 是否健康
    message: str = ""                 # 状态消息
    last_check: float = 0.0           # 上次检查时间戳
    error_count: int = 0              # 错误计数
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "healthy": self.healthy,
            "message": self.message,
            "last_check": self.last_check,
            "error_count": self.error_count,
            "metadata": self.metadata
        }


@dataclass
class AdapterCapabilities:
    """
    适配器能力描述
    """
    supports_streaming: bool = False  # 支持流式输出
    supports_batch: bool = False      # 支持批量执行
    supports_async: bool = True       # 支持异步执行
    max_concurrent: int = 1           # 最大并发数
    tools: List[str] = field(default_factory=list)  # 支持的工具列表

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "supports_streaming": self.supports_streaming,
            "supports_batch": self.supports_batch,
            "supports_async": self.supports_async,
            "max_concurrent": self.max_concurrent,
            "tools": self.tools
        }
