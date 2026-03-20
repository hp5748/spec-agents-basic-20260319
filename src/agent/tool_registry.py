"""
工具注册表

中心化管理所有类型的工具（Skills/MCP/SubAgent/Custom）。

核心功能：
- 统一注册工具
- 查询和检索工具
- 生成 OpenAPI Schema
- 动态添加/移除工具
- 线程安全
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional

from .tool import Tool, ToolType, ToolResult, create_tool_from_function


logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    工具注册表

    管理所有类型工具的中心化注册表。

    使用方式：
        registry = ToolRegistry()

        # 注册自定义工具
        @registry.register("my_tool")
        def my_function(param1: str) -> str:
            return f"Hello {param1}"

        # 注册 Skill
        registry.register_skill("my_skill", description="...")

        # 注册 MCP 工具
        registry.register_mcp_tool("server", "tool", "...", handler=...)

        # 查询工具
        tool = registry.get("my_tool")
        tools = registry.list_tools(type=ToolType.SKILL)

        # 生成 OpenAPI Schema
        schema = registry.to_openapi_schema()

        # 执行工具
        result = await registry.execute("my_tool", param1="World")
    """

    def __init__(self):
        """初始化注册表"""
        # 工具存储：name -> Tool
        self._tools: Dict[str, Tool] = {}

        # 类型索引：type -> [names]
        self._type_index: Dict[ToolType, List[str]] = {
            ToolType.SKILL: [],
            ToolType.MCP: [],
            ToolType.SUBAGENT: [],
            ToolType.CUSTOM: []
        }

        # 锁（用于线程安全）
        self._lock = asyncio.Lock()

    def register(
        self,
        name: Optional[str] = None,
        description: str = "",
        parameters: Optional[List[Any]] = None
    ) -> Callable:
        """
        装饰器：注册函数为工具

        Args:
            name: 工具名称（默认使用函数名）
            description: 工具描述
            parameters: 参数列表

        Returns:
            装饰器函数

        示例：
            @registry.register("my_tool", description="My custom tool")
            def my_function(text: str) -> str:
                return f"Processed: {text}"
        """
        def decorator(func: Callable) -> Callable:
            tool = create_tool_from_function(func, name)
            if description:
                tool.description = description
            if parameters:
                tool.parameters = parameters

            self._register_sync(tool)
            return func

        return decorator

    def register_tool(self, tool: Tool) -> None:
        """
        注册工具

        Args:
            tool: 工具实例
        """
        self._register_sync(tool)

    def _register_sync(self, tool: Tool) -> None:
        """同步注册工具（内部方法）"""
        if tool.name in self._tools:
            logger.warning(f"工具 {tool.name} 已存在，将被覆盖")

        self._tools[tool.name] = tool

        # 更新类型索引
        if tool.type not in self._type_index:
            self._type_index[tool.type] = []

        if tool.name not in self._type_index[tool.type]:
            self._type_index[tool.type].append(tool.name)

        logger.info(f"已注册工具: {tool.name} (类型: {tool.type.value})")

    def register_skill(
        self,
        skill_name: str,
        description: str,
        handler: Optional[Callable] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tool:
        """
        注册 Skill 工具

        Args:
            skill_name: Skill 名称
            description: 描述
            handler: 执行函数
            metadata: 元数据

        Returns:
            Tool: 工具实例
        """
        tool = Tool.from_skill(skill_name, description, metadata)
        if handler:
            tool.handler = handler

        self._register_sync(tool)
        return tool

    def register_mcp_tool(
        self,
        server_name: str,
        tool_name: str,
        description: str,
        handler: Callable,
        parameters: Optional[List[Any]] = None
    ) -> Tool:
        """
        注册 MCP 工具

        Args:
            server_name: MCP 服务器名称
            tool_name: 工具名称
            description: 描述
            handler: 执行函数
            parameters: 参数列表

        Returns:
            Tool: 工具实例
        """
        tool = Tool.from_mcp_tool(
            server_name=server_name,
            tool_name=tool_name,
            description=description,
            parameters=parameters or [],
            handler=handler
        )

        self._register_sync(tool)
        return tool

    def register_subagent(
        self,
        agent_id: str,
        description: str,
        handler: Callable,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tool:
        """
        注册 SubAgent 工具

        Args:
            agent_id: Agent ID
            description: 描述
            handler: 执行函数
            metadata: 元数据

        Returns:
            Tool: 工具实例
        """
        tool = Tool.from_subagent(agent_id, description, handler, metadata)
        self._register_sync(tool)
        return tool

    def unregister(self, tool_name: str) -> bool:
        """
        注销工具

        Args:
            tool_name: 工具名称

        Returns:
            bool: 是否成功
        """
        if tool_name not in self._tools:
            logger.warning(f"工具 {tool_name} 不存在")
            return False

        tool = self._tools[tool_name]

        # 从类型索引中移除
        if tool.type in self._type_index and tool_name in self._type_index[tool.type]:
            self._type_index[tool.type].remove(tool_name)

        # 从注册表中移除
        del self._tools[tool_name]

        logger.info(f"已注销工具: {tool_name}")
        return True

    def get(self, tool_name: str) -> Optional[Tool]:
        """
        获取工具

        Args:
            tool_name: 工具名称

        Returns:
            Optional[Tool]: 工具实例，不存在返回 None
        """
        return self._tools.get(tool_name)

    def list_tools(
        self,
        type: Optional[ToolType] = None,
        enabled_only: bool = True
    ) -> List[Tool]:
        """
        列出工具

        Args:
            type: 工具类型过滤（None 表示全部）
            enabled_only: 是否只返回启用的工具

        Returns:
            List[Tool]: 工具列表
        """
        tools = []

        if type:
            # 按类型过滤
            names = self._type_index.get(type, [])
            for name in names:
                tool = self._tools.get(name)
                if tool and (not enabled_only or tool.enabled):
                    tools.append(tool)
        else:
            # 全部
            for tool in self._tools.values():
                if not enabled_only or tool.enabled:
                    tools.append(tool)

        return tools

    def list_tool_names(
        self,
        type: Optional[ToolType] = None,
        enabled_only: bool = True
    ) -> List[str]:
        """
        列出工具名称

        Args:
            type: 工具类型过滤
            enabled_only: 是否只返回启用的工具

        Returns:
            List[str]: 工具名称列表
        """
        tools = self.list_tools(type, enabled_only)
        return [tool.name for tool in tools]

    def enable(self, tool_name: str) -> bool:
        """
        启用工具

        Args:
            tool_name: 工具名称

        Returns:
            bool: 是否成功
        """
        tool = self.get(tool_name)
        if not tool:
            return False

        tool.enabled = True
        logger.info(f"已启用工具: {tool_name}")
        return True

    def disable(self, tool_name: str) -> bool:
        """
        禁用工具

        Args:
            tool_name: 工具名称

        Returns:
            bool: 是否成功
        """
        tool = self.get(tool_name)
        if not tool:
            return False

        tool.enabled = False
        logger.info(f"已禁用工具: {tool_name}")
        return True

    async def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """
        执行工具

        Args:
            tool_name: 工具名称
            **kwargs: 工具参数

        Returns:
            ToolResult: 执行结果
        """
        tool = self.get(tool_name)

        if not tool:
            return ToolResult(
                success=False,
                error=f"工具 {tool_name} 不存在"
            )

        return await tool.execute(**kwargs)

    def to_openapi_schema(self, group_by_type: bool = False) -> Dict[str, Any]:
        """
        生成 OpenAPI 规范的 JSON Schema

        Args:
            group_by_type: 是否按类型分组

        Returns:
            Dict: OpenAPI Schema
        """
        tools = self.list_tools(enabled_only=True)

        if group_by_type:
            # 按类型分组
            schema = {
                "tools": {}
            }

            for tool_type in ToolType:
                type_tools = [t for t in tools if t.type == tool_type]
                if type_tools:
                    schema["tools"][tool_type.value] = [
                        tool.to_openapi_schema() for tool in type_tools
                    ]
        else:
            # 扁平化列表
            schema = {
                "tools": [tool.to_openapi_schema() for tool in tools]
            }

        # 添加统计信息
        schema["stats"] = {
            "total": len(tools),
            "by_type": {}
        }

        for tool_type in ToolType:
            count = len([t for t in tools if t.type == tool_type])
            if count > 0:
                schema["stats"]["by_type"][tool_type.value] = count

        return schema

    def count(self, type: Optional[ToolType] = None, enabled_only: bool = True) -> int:
        """
        统计工具数量

        Args:
            type: 工具类型
            enabled_only: 是否只统计启用的工具

        Returns:
            int: 工具数量
        """
        return len(self.list_tools(type, enabled_only))

    def clear(self) -> None:
        """清空所有工具"""
        self._tools.clear()
        for tool_type in self._type_index:
            self._type_index[tool_type].clear()
        logger.info("已清空工具注册表")

    def __len__(self) -> int:
        """返回工具总数"""
        return len(self._tools)

    def __contains__(self, tool_name: str) -> bool:
        """判断工具是否存在"""
        return tool_name in self._tools

    def __iter__(self):
        """迭代所有工具"""
        return iter(self._tools.values())


# 全局单例
_global_registry: Optional[ToolRegistry] = None


def get_global_registry() -> ToolRegistry:
    """
    获取全局工具注册表

    Returns:
        ToolRegistry: 全局注册表实例
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def reset_global_registry() -> None:
    """重置全局注册表（主要用于测试）"""
    global _global_registry
    _global_registry = None
