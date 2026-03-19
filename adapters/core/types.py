"""
核心类型定义

定义适配器模块所需的所有数据类型。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class AdapterType(Enum):
    """适配器类型枚举"""
    PYTHON = "python"    # Python 执行器（Skill 内置）
    HTTP = "http"        # HTTP REST API
    MCP = "mcp"          # Model Context Protocol
    SHELL = "shell"      # Shell/CLI 工具


class ExecutionStatus(Enum):
    """执行状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RETRYING = "retrying"
    FALLBACK = "fallback"


@dataclass
class AdapterConfig:
    """
    适配器配置

    Attributes:
        type: 适配器类型
        name: 适配器名称（唯一标识）
        enabled: 是否启用
        timeout: 执行超时时间（秒）
        retry_count: 重试次数
        metadata: 额外配置元数据
    """
    type: AdapterType
    name: str
    enabled: bool = True
    timeout: int = 30
    retry_count: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """验证配置"""
        if not self.name:
            raise ValueError("适配器名称不能为空")
        if self.timeout <= 0:
            raise ValueError("超时时间必须大于 0")


@dataclass
class AdapterResult:
    """
    适配器执行结果

    Attributes:
        success: 是否执行成功
        data: 返回数据
        error: 错误信息（如果失败）
        metadata: 额外元数据（如状态码、执行时间等）
    """
    success: bool
    data: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class SkillContext:
    """
    技能执行上下文

    Attributes:
        session_id: 会话 ID
        user_input: 用户输入
        intent: 识别的意图
        chat_history: 对话历史
        metadata: 额外上下文信息
    """
    session_id: str
    user_input: str
    intent: str
    chat_history: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后处理"""
        if not self.session_id:
            self.session_id = "default"


@dataclass
class ExecutionTrace:
    """
    执行追踪记录

    Attributes:
        trace_id: 追踪 ID
        adapter_name: 适配器名称
        status: 执行状态
        start_time: 开始时间
        end_time: 结束时间
        attempts: 尝试次数
        result: 最终结果
    """
    trace_id: str
    adapter_name: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    attempts: int = 0
    result: Optional[AdapterResult] = None

    @property
    def elapsed_time(self) -> Optional[float]:
        """计算执行耗时"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


@dataclass
class SchemaDefinition:
    """
    Schema 定义（JSON Schema 格式）

    Attributes:
        name: Schema 名称
        schema: JSON Schema 定义
        required: 必填字段列表
    """
    name: str
    schema: Dict[str, Any]
    required: List[str] = field(default_factory=list)
