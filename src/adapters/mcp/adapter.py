"""
MCP Adapter 实现

提供 MCP (Model Context Protocol) 适配器，继承 BaseAdapter 接口。

功能特性：
- 支持 STDIO、HTTP、SSE 传输方式
- 兼容 .claude/mcp.json 和 config/mcp.yaml 配置格式
- 自动注册 MCP 工具到 ToolRegistry
- 统一的错误处理和重试机制
"""

import logging
from typing import Any, Dict, List

from ..core import (
    BaseAdapter,
    AdapterConfig,
    AdapterType,
    AdapterCapabilities,
    ToolRequest,
    ToolResponse
)

from .client import MCPClient
from .config import MCPConfigLoader


logger = logging.getLogger(__name__)


class MCPAdapter(BaseAdapter):
    """
    MCP 适配器

    实现 BaseAdapter 接口，提供 MCP 协议支持。

    配置示例：
        ```yaml
        mcp:
          sqlite:
            enabled: true
            transport: stdio
            command: uvx
            args: ["--no-cache", "mcp-server-sqlite", "--db-path", "data/users.db"]
        ```

    使用方式：
        ```python
        from src.adapters.mcp import MCPAdapter

        config = AdapterConfig(
            type=AdapterType.MCP,
            name="mcp_adapter",
            metadata={"project_root": "."}
        )

        adapter = MCPAdapter(config)
        await adapter.initialize()

        # 执行工具调用
        request = ToolRequest(
            tool_name="sqlite_query",
            parameters={"sql": "SELECT * FROM users"}
        )
        response = await adapter.execute(request)
        ```
    """

    def __init__(self, config: AdapterConfig):
        """
        初始化 MCP 适配器

        Args:
            config: 适配器配置
        """
        super().__init__(config)

        # 获取项目根目录
        self._project_root = self.config.metadata.get("project_root", ".")

        # 创建 MCP 客户端
        self._mcp_client = MCPClient(project_root=self._project_root)

        # 工具映射：tool_name -> (server_name, actual_tool_name)
        self._tool_map: Dict[str, tuple[str, str]] = {}

        # 设置能力
        self._capabilities = AdapterCapabilities(
            supports_streaming=False,
            supports_batch=True,
            supports_async=True,
            max_concurrent=10,
            tools=[]  # 初始化后填充
        )

    async def initialize(self) -> None:
        """
        初始化适配器

        - 加载 MCP 配置
        - 连接所有 MCP 服务器
        - 索引所有可用工具
        """
        try:
            logger.info(f"MCPAdapter [{self.config.name}] 正在初始化...")

            # 初始化 MCP 客户端
            await self._mcp_client.initialize()

            # 索引所有工具
            await self._index_tools()

            logger.info(
                f"MCPAdapter [{self.config.name}] 初始化完成，"
                f"已索引 {len(self._tool_map)} 个工具"
            )

        except Exception as e:
            logger.error(f"MCPAdapter [{self.config.name}] 初始化失败: {e}", exc_info=True)
            self._increment_error_count()
            raise

    async def execute(self, request: ToolRequest) -> ToolResponse:
        """
        执行工具调用

        Args:
            request: 工具调用请求

        Returns:
            ToolResponse: 执行响应
        """
        # 验证请求
        if not await self.validate_request(request):
            return ToolResponse.from_error("Invalid request", request.tool_name)

        # 查找工具对应的 MCP 服务器
        tool_mapping = self._tool_map.get(request.tool_name)
        if not tool_mapping:
            return ToolResponse.from_error(
                f"Tool not found: {request.tool_name}",
                request.tool_name
            )

        server_name, actual_tool_name = tool_mapping

        # 使用追踪包装器执行
        return await self._execute_with_tracking(
            request.tool_name,
            self._call_mcp_tool,
            server_name,
            actual_tool_name,
            request.parameters
        )

    async def _call_mcp_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> ToolResponse:
        """
        调用 MCP 工具

        Args:
            server_name: MCP 服务器名称
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            ToolResponse: 执行结果
        """
        try:
            result = await self._mcp_client.call_tool(server_name, tool_name, arguments)

            if result.get("success"):
                return ToolResponse.from_success(result.get("data"), tool_name)
            else:
                return ToolResponse.from_error(result.get("error", "Unknown error"), tool_name)

        except Exception as e:
            logger.error(f"MCP 工具调用失败 [{server_name}/{tool_name}]: {e}", exc_info=True)
            return ToolResponse.from_error(str(e), tool_name)

    async def shutdown(self) -> None:
        """
        关闭适配器

        断开所有 MCP 服务器连接
        """
        try:
            await self._mcp_client.shutdown()
            logger.info(f"MCPAdapter [{self.config.name}] 已关闭")
        except Exception as e:
            logger.error(f"MCPAdapter [{self.config.name}] 关闭失败: {e}")

    def get_capabilities(self) -> AdapterCapabilities:
        """
        获取适配器能力描述

        Returns:
            AdapterCapabilities: 能力描述
        """
        # 更新工具列表
        self._capabilities.tools = list(self._tool_map.keys())
        return self._capabilities

    async def _index_tools(self) -> None:
        """
        索引所有 MCP 服务器的工具

        构建 tool_name -> (server_name, actual_tool_name) 的映射
        """
        self._tool_map.clear()

        all_tools = await self._mcp_client.list_all_tools()

        for server_name, tools in all_tools.items():
            for tool in tools:
                tool_name = tool.get("name", "")

                # 构建完整工具名：server_name:tool_name
                full_tool_name = f"{server_name}:{tool_name}"

                self._tool_map[full_tool_name] = (server_name, tool_name)

                logger.debug(f"索引工具: {full_tool_name}")

    async def list_tools(self) -> List[str]:
        """
        列出所有可用的工具

        Returns:
            List[str]: 工具名称列表
        """
        return list(self._tool_map.keys())

    async def health_check(self) -> Any:
        """
        健康检查

        检查所有 MCP 服务器的连接状态

        Returns:
            AdapterHealthStatus: 健康状态
        """
        from ..core.types import AdapterHealthStatus

        status = await super().health_check()

        # 检查 MCP 客户端连接状态
        servers = self._mcp_client.list_servers()
        connected_count = len(servers)

        status.metadata = {
            "connected_servers": connected_count,
            "total_tools": len(self._tool_map),
            "servers": servers
        }

        status.message = (
            f"MCP Adapter: {connected_count} servers connected, "
            f"{len(self._tool_map)} tools available"
        )

        return status
