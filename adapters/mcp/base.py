"""
MCP 适配器

支持 Model Context Protocol (MCP)，通过 stdio 与 MCP Server 通信。

参考项目：
- modelcontextprotocol/servers
"""

from typing import Any, Dict, Optional
import asyncio
import json
import logging
import time

from adapters.core.base_adapter import BaseAdapter
from adapters.core.types import AdapterConfig, AdapterResult, SkillContext


logger = logging.getLogger(__name__)


class MCPAdapter(BaseAdapter):
    """
    MCP 适配器

    支持 Model Context Protocol (MCP)，通过 stdio 与 MCP Server 通信。

    配置示例:
        config = AdapterConfig(
            type=AdapterType.MCP,
            name="fetch-server",
            metadata={
                "server_path": "adapters/mcp/servers/fetch-server/server.py",
                "transport": "stdio"
            }
        )
    """

    def __init__(self, config: AdapterConfig):
        super().__init__(config)
        self._process: Optional[asyncio.subprocess.Process] = None
        self._request_id = 0
        self._initialized = False

    async def initialize(self) -> bool:
        """
        初始化 MCP 适配器

        - 启动 MCP Server 进程
        - 发送 initialize 请求
        """
        server_path = self.config.metadata.get("server_path")
        transport = self.config.metadata.get("transport", "stdio")

        if not server_path:
            logger.error("未配置 MCP Server 路径")
            return False

        if transport != "stdio":
            logger.error(f"不支持的传输方式: {transport}")
            return False

        try:
            # 启动 MCP Server 进程
            self._process = await asyncio.create_subprocess_exec(
                "python", server_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # 发送初始化请求
            response = await self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "skill-adapter",
                    "version": "1.0.0"
                }
            })

            if "error" in response:
                logger.error(f"MCP 初始化失败: {response['error']}")
                return False

            self._initialized = True
            logger.info(f"MCP 适配器初始化完成: {self.name}")
            return True

        except Exception as e:
            logger.error(f"MCP 适配器初始化失败: {e}")
            return False

    async def _send_request(
        self,
        method: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        发送 JSON-RPC 请求

        Args:
            method: 方法名
            params: 参数

        Returns:
            Dict: 响应数据
        """
        if not self._process or not self._process.stdin:
            raise RuntimeError("MCP Server 进程未启动")

        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params
        }

        try:
            # 发送请求
            request_str = json.dumps(request) + "\n"
            self._process.stdin.write(request_str.encode())
            await self._process.stdin.drain()

            # 读取响应
            response_line = await asyncio.wait_for(
                self._process.stdout.readline(),
                timeout=self.config.timeout
            )

            return json.loads(response_line.decode())

        except asyncio.TimeoutError:
            return {"error": {"code": -1, "message": "请求超时"}}
        except Exception as e:
            return {"error": {"code": -1, "message": str(e)}}

    async def execute(
        self,
        context: SkillContext,
        input_data: Dict[str, Any]
    ) -> AdapterResult:
        """
        调用 MCP Tool

        Args:
            context: 技能执行上下文
            input_data: 输入数据，包含 tool_name 和 arguments

        Returns:
            AdapterResult: 执行结果
        """
        if not self._initialized:
            return AdapterResult(
                success=False,
                data=None,
                error="MCP 适配器未初始化"
            )

        tool_name = input_data.get("tool_name", context.intent)
        arguments = input_data.get("arguments", input_data)

        try:
            response = await self._send_request("tools/call", {
                "name": tool_name,
                "arguments": arguments
            })

            if "error" in response:
                return AdapterResult(
                    success=False,
                    data=None,
                    error=response["error"].get("message", "未知错误")
                )

            result = response.get("result", {})
            content = result.get("content", [])

            return AdapterResult(
                success=True,
                data=content,
                metadata={
                    "tool_name": tool_name,
                    "response_id": response.get("id"),
                }
            )

        except Exception as e:
            return AdapterResult(
                success=False,
                data=None,
                error=f"MCP 调用失败: {str(e)}"
            )

    async def health_check(self) -> bool:
        """健康检查"""
        if not self._process:
            return False
        return self._process.returncode is None

    async def cleanup(self):
        """关闭 MCP Server 进程"""
        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self._process.kill()
                await self._process.wait()
            except Exception as e:
                logger.error(f"关闭 MCP Server 失败: {e}")
            finally:
                self._process = None
                self._initialized = False

    async def list_tools(self) -> list:
        """获取可用工具列表"""
        if not self._initialized:
            return []

        response = await self._send_request("tools/list", {})
        if "error" in response:
            return []

        return response.get("result", {}).get("tools", [])
