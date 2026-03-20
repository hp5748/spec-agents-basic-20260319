"""
MCP 客户端

管理所有 MCP 服务器的连接和调用。
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from .config import MCPConfigLoader, MCPServerConfig, MCPConfig
from .transport.stdio import STDIOTransport
from .transport.http import HTTPTransport


logger = logging.getLogger(__name__)


class MCPClient:
    """
    MCP 客户端

    管理所有 MCP 服务器的连接和调用。

    使用方式：
        client = MCPClient()
        await client.initialize()

        # 调用工具
        result = await client.call_tool("filesystem", "read_file", {"path": "./test.txt"})

        # 列出工具
        tools = await client.list_tools("filesystem")
    """

    def __init__(self, project_root: str = "."):
        self._loader = MCPConfigLoader(project_root)
        self._config: Optional[MCPConfig] = None
        self._transports: Dict[str, Any] = {}  # server_name -> transport

    async def initialize(self) -> None:
        """初始化所有服务器连接"""
        self._config = self._loader.load()

        servers = self._config.get_all_servers()

        if not servers:
            logger.info("未配置 MCP 服务器")
            return

        # 并行连接所有服务器
        connection_tasks = []
        for name, server_config in servers.items():
            if server_config.disabled:
                logger.info(f"服务器 {name} 已禁用，跳过")
                continue

            connection_tasks.append(self._connect_server(name, server_config))

        if connection_tasks:
            results = await asyncio.gather(*connection_tasks, return_exceptions=True)
            success_count = sum(1 for r in results if not isinstance(r, Exception))
            logger.info(f"MCP 客户端初始化完成: {success_count}/{len(connection_tasks)} 个服务器已连接")

    async def _connect_server(self, name: str, config: MCPServerConfig) -> None:
        """连接单个服务器"""
        try:
            if config.transport == "stdio":
                transport = STDIOTransport(config)
            elif config.transport == "http":
                transport = HTTPTransport(config)
            else:
                raise ValueError(f"不支持的传输方式: {config.transport}")

            await transport.connect()
            self._transports[name] = transport

        except Exception as e:
            logger.error(f"连接 MCP 服务器 {name} 失败: {e}")
            raise

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        调用 MCP 服务器的工具

        Args:
            server_name: MCP 服务器名称
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            Dict: 执行结果 {"success": bool, "data": ..., "error": ...}
        """
        if server_name not in self._transports:
            return {
                "success": False,
                "error": f"MCP 服务器 {server_name} 未连接"
            }

        transport = self._transports[server_name]
        try:
            return await transport.call_tool(tool_name, arguments)
        except Exception as e:
            logger.error(f"调用工具失败 [{server_name}/{tool_name}]: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def list_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """
        列出服务器的所有工具

        Args:
            server_name: MCP 服务器名称

        Returns:
            List[Dict]: 工具列表
        """
        if server_name not in self._transports:
            logger.warning(f"MCP 服务器 {server_name} 未连接")
            return []

        transport = self._transports[server_name]
        try:
            return await transport.list_tools()
        except Exception as e:
            logger.error(f"获取工具列表失败 [{server_name}]: {e}")
            return []

    async def list_all_tools(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        列出所有服务器的工具

        Returns:
            Dict: {server_name: [tools]}
        """
        result = {}

        for server_name in self._transports.keys():
            tools = await self.list_tools(server_name)
            result[server_name] = tools

        return result

    def list_servers(self) -> List[str]:
        """列出所有已连接的服务器"""
        return list(self._transports.keys())

    async def shutdown(self) -> None:
        """关闭所有连接"""
        if not self._transports:
            return

        shutdown_tasks = []
        for name, transport in self._transports.items():
            shutdown_tasks.append(self._disconnect_server(name, transport))

        await asyncio.gather(*shutdown_tasks, return_exceptions=True)
        self._transports.clear()
        logger.info("MCP 客户端已关闭")

    async def _disconnect_server(self, name: str, transport: Any) -> None:
        """断开单个服务器"""
        try:
            await transport.disconnect()
        except Exception as e:
            logger.error(f"断开 {name} 失败: {e}")
