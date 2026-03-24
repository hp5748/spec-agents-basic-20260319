"""
工具定义模块

实现"万物皆工具"理念，统一管理 Skills、MCP、SubAgent 等所有能力。

核心概念：
- Tool: 统一的工具抽象
- ToolType: 工具类型枚举
- ToolParameter: 参数定义
- ToolResult: 执行结果
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
import logging


logger = logging.getLogger(__name__)


class ToolType(Enum):
    """工具类型枚举"""
    SKILL = "skill"           # Skill 工具
    MCP = "mcp"              # MCP 工具
    SUBAGENT = "subagent"    # SubAgent 工具
    CUSTOM = "custom"        # 自定义工具


@dataclass
class ToolParameter:
    """
    工具参数定义

    支持生成 OpenAPI Schema
    """
    name: str                    # 参数名
    type: str                    # 参数类型 (string, number, boolean, array, object)
    description: str = ""        # 参数描述
    required: bool = False       # 是否必需
    default: Any = None          # 默认值
    enum: Optional[List[Any]] = None  # 枚举值

    def to_openapi(self) -> Dict[str, Any]:
        """转换为 OpenAPI 参数格式"""
        param: Dict[str, Any] = {
            "type": self.type,
            "description": self.description
        }

        if self.enum:
            param["enum"] = self.enum

        if self.default is not None:
            param["default"] = self.default

        return param


@dataclass
class ToolResult:
    """
    工具执行结果

    统一的返回格式
    """
    success: bool               # 执行是否成功
    data: Any = None            # 返回数据
    error: Optional[str] = None # 错误信息
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据


@dataclass
class Tool:
    """
    统一的工具抽象

    支持：
    - Skill 工具（来自 skills/ 目录）
    - MCP 工具（来自 MCP Server）
    - SubAgent 工具（来自 subagents/ 目录）
    - 自定义工具（动态注册的函数）
    """

    # 基本信息
    name: str                          # 工具唯一标识
    type: ToolType                     # 工具类型
    description: str                   # 工具描述

    # 执行相关
    handler: Optional[Callable] = None # 执行函数（同步或异步）
    parameters: List[ToolParameter] = field(default_factory=list)  # 参数列表

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 状态
    enabled: bool = True               # 是否启用

    def to_openapi_schema(self) -> Dict[str, Any]:
        """
        生成 OpenAPI 规范的 JSON Schema

        Returns:
            Dict: OpenAPI 格式的工具定义
        """
        # 构建参数 Schema
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = param.to_openapi()
            if param.required:
                required.append(param.name)

        # 构建 OpenAI Function Calling 格式
        parameters_schema = {
            "type": "object",
            "properties": properties
        }

        if required:
            parameters_schema["required"] = required

        schema = {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": parameters_schema
            }
        }

        # 添加自定义元数据（在 function 层级）
        schema["function"]["x-tool-type"] = self.type.value
        if self.metadata:
            schema["function"]["x-metadata"] = self.metadata

        return schema

    async def execute(self, **kwargs) -> ToolResult:
        """
        执行工具

        Args:
            **kwargs: 工具参数

        Returns:
            ToolResult: 执行结果
        """
        if not self.enabled:
            return ToolResult(
                success=False,
                error=f"工具 {self.name} 已禁用"
            )

        if not self.handler:
            return ToolResult(
                success=False,
                error=f"工具 {self.name} 没有执行函数"
            )

        try:
            # 调用处理函数
            if callable(self.handler):
                # 判断是否是协程函数
                import inspect
                if inspect.iscoroutinefunction(self.handler):
                    result = await self.handler(**kwargs)
                else:
                    result = self.handler(**kwargs)

                # 统一返回格式
                if isinstance(result, ToolResult):
                    return result
                elif isinstance(result, dict):
                    if "success" in result:
                        return ToolResult(
                            success=result.get("success", False),
                            data=result.get("data"),
                            error=result.get("error"),
                            metadata=result.get("metadata", {})
                        )
                    else:
                        return ToolResult(success=True, data=result)
                else:
                    return ToolResult(success=True, data=result)
            else:
                return ToolResult(
                    success=False,
                    error=f"工具 {self.name} 的 handler 不是可调用对象"
                )

        except Exception as e:
            logger.error(f"工具执行失败 [{self.name}]: {e}", exc_info=True)
            return ToolResult(
                success=False,
                error=str(e)
            )

    @classmethod
    def from_skill(
        cls,
        skill_name: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "Tool":
        """
        从 Skill 创建工具

        Args:
            skill_name: Skill 名称
            description: Skill 描述
            metadata: 元数据

        Returns:
            Tool: 工具实例
        """
        return cls(
            name=f"skill.{skill_name}",
            type=ToolType.SKILL,
            description=description,
            metadata=metadata or {},
            parameters=[
                ToolParameter(
                    name="user_input",
                    type="string",
                    description="用户输入",
                    required=True
                ),
                ToolParameter(
                    name="context",
                    type="object",
                    description="执行上下文",
                    required=False
                )
            ]
        )

    @classmethod
    def from_mcp_tool(
        cls,
        server_name: str,
        tool_name: str,
        description: str,
        parameters: List[ToolParameter],
        handler: Callable
    ) -> "Tool":
        """
        从 MCP 工具创建工具

        Args:
            server_name: MCP 服务器名称
            tool_name: 工具名称
            description: 工具描述
            parameters: 参数列表
            handler: 执行函数

        Returns:
            Tool: 工具实例
        """
        return cls(
            name=f"mcp.{server_name}.{tool_name}",
            type=ToolType.MCP,
            description=description,
            handler=handler,
            parameters=parameters,
            metadata={
                "server_name": server_name,
                "tool_name": tool_name
            }
        )

    @classmethod
    def from_subagent(
        cls,
        agent_id: str,
        description: str,
        handler: Callable,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "Tool":
        """
        从 SubAgent 创建工具

        Args:
            agent_id: Agent ID
            description: 描述
            handler: 执行函数
            metadata: 元数据

        Returns:
            Tool: 工具实例
        """
        return cls(
            name=f"subagent.{agent_id}",
            type=ToolType.SUBAGENT,
            description=description,
            handler=handler,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="查询内容",
                    required=True
                ),
                ToolParameter(
                    name="context",
                    type="object",
                    description="上下文信息",
                    required=False
                )
            ],
            metadata=metadata or {}
        )

    @classmethod
    def from_function(
        cls,
        name: str,
        func: Callable,
        description: str = "",
        parameters: Optional[List[ToolParameter]] = None
    ) -> "Tool":
        """
        从函数创建自定义工具

        Args:
            name: 工具名称
            func: 函数
            description: 描述
            parameters: 参数列表

        Returns:
            Tool: 工具实例
        """
        return cls(
            name=name,
            type=ToolType.CUSTOM,
            description=description or func.__doc__ or f"Custom tool: {name}",
            handler=func,
            parameters=parameters or []
        )


def create_tool_from_function(func: Callable, name: Optional[str] = None) -> Tool:
    """
    便捷函数：从函数创建工具

    自动从函数签名提取参数信息

    Args:
        func: 函数
        name: 工具名称（默认使用函数名）

    Returns:
        Tool: 工具实例
    """
    import inspect

    tool_name = name or func.__name__
    description = func.__doc__ or f"Function: {tool_name}"

    # 从函数签名提取参数
    parameters = []
    sig = inspect.signature(func)

    for param_name, param in sig.parameters.items():
        # 跳过 self 和 cls
        if param_name in ("self", "cls"):
            continue

        # 推断类型
        param_type = "string"
        if param.annotation != inspect.Parameter.empty:
            annotation_str = str(param.annotation)
            if "int" in annotation_str or "float" in annotation_str:
                param_type = "number"
            elif "bool" in annotation_str:
                param_type = "boolean"
            elif "list" in annotation_str or "List" in annotation_str:
                param_type = "array"
            elif "dict" in annotation_str or "Dict" in annotation_str:
                param_type = "object"

        # 判断是否必需
        required = param.default == inspect.Parameter.empty

        parameters.append(ToolParameter(
            name=param_name,
            type=param_type,
            description=f"Parameter: {param_name}",
            required=required
        ))

    return Tool.from_function(
        name=tool_name,
        func=func,
        description=description,
        parameters=parameters
    )
