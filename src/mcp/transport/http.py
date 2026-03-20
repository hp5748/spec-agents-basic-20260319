"""
MCP HTTP 传输

通过 HTTP 协议与远程 MCP Server 通信。
"""

import asyncio
import json
import logging
from typing import Any, Dict, List

import httpx


logger = logging.getLogger(__name__)


class HTTPTransport:
    """
    HTTP 传输

    通过 HTTP 协议与远程 MCP Server 通信。
    """

    def __init__(self, config):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
        self._request_id = 0

    async def connect(self) -> None:
        """建立连接"""
        # 准备请求头
        headers = {
            "Content-Type": "application/json",
            **self.config.headers
        }

        # 展开环境变量
        headers = self._expand_env_vars(headers)

        self._client = httpx.AsyncClient(
            base_url=self.config.url,
            headers=headers,
            timeout=self.config.env.get("timeout", 30)
        )

        # 测试连接
        try:
            response = await self._client.post("/", json={"jsonrpc": "2.0", "method": "ping", "id": 1})
            if response.status_code == 200:
                self.config._status = "running"
                logger.info(f"MCP Server {self.config.name} 已连接")
        except Exception as e:
            logger.error(f"连接 MCP Server {self.config.name} 失败: {e}")
            self.config._status = "error"
            raise

    async def disconnect(self) -> None:
        """断开连接"""
        if self._client:
            await self._client.aclose()
            self._client = None
            self.config._status = "stopped"
            logger.info(f"MCP Server {self.config.name} 已断开")

    def _expand_env_vars(self, data: Dict[str, str]) -> Dict[str, str]:
        """展开环境变量"""
        import os
        result = {}
        for key, value in data.items():
            if isinstance(value, str) and value.startswith("$"):
                var_name = value[1:]
                result[key] = os.getenv(var_name, value)
            else:
                result[key] = value
        return result

    async def _send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """发送 JSON-RPC 请求"""
        if not self._client:
            raise RuntimeError("MCP Server 未连接")

        self._request_id += 1

        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or {}
        }

        try:
            response = await self._client.post("/", json=request)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP 请求失败: {e}")
            raise

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用工具"""
        response = await self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })

        if "error" in response:
            return {
                "success": False,
                "error": response["error"]
            }

        return {
            "success": True,
            "data": response.get("result", {})
        }

    async def list_tools(self) -> List[Dict[str, Any]]:
        """列出所有工具"""
        response = await self._send_request("tools/list", {})

        if "error" in response:
            logger.error(f"获取工具列表失败: {response['error']}")
            return []

        return response.get("result", {}).get("tools", [])
