"""
MCP STDIO 传输

通过标准输入/输出与本地 MCP Server 进程通信。
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from ..config import MCPServerConfig


logger = logging.getLogger(__name__)


class STDIOTransport:
    """
    STDIO 传输

    启动本地 MCP Server 进程，通过 stdin/stdout 通信。
    """

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self._process: Optional[asyncio.subprocess.Process] = None
        self._request_id = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}

    async def connect(self) -> None:
        """启动 MCP Server 进程"""
        if self._process and self._process.returncode is None:
            logger.warning(f"MCP Server {self.config.name} 已在运行")
            return

        # 构建环境变量
        env = None
        if self.config.env:
            import os
            env = os.environ.copy()
            env.update(self.config.env)

        # 启动进程
        cmd = [self.config.command] + self.config.args
        logger.info(f"启动 MCP Server: {' '.join(cmd)}")

        try:
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )

            # 启动响应监听任务
            asyncio.create_task(self._read_responses())

            # 等待进程启动
            await asyncio.sleep(0.5)

            if self._process.returncode is not None:
                raise RuntimeError(f"MCP Server 启动失败，退出码: {self._process.returncode}")

            self.config._status = "running"
            logger.info(f"MCP Server {self.config.name} 已启动")

        except Exception as e:
            logger.error(f"启动 MCP Server {self.config.name} 失败: {e}")
            self.config._status = "error"
            raise

    async def disconnect(self) -> None:
        """断开连接"""
        if self._process:
            try:
                self._process.terminate()
                await self._process.wait()
                logger.info(f"MCP Server {self.config.name} 已停止")
            except Exception as e:
                logger.error(f"停止 MCP Server {self.config.name} 失败: {e}")
            finally:
                self._process = None
                self.config._status = "stopped"

    async def _read_responses(self) -> None:
        """读取进程响应"""
        if not self._process or not self._process.stdout:
            return

        try:
            while True:
                line = await self._process.stdout.readline()
                if not line:
                    break

                try:
                    response = json.loads(line.decode("utf-8"))
                    await self._handle_response(response)
                except json.JSONDecodeError:
                    logger.warning(f"无效的 JSON 响应: {line}")

        except Exception as e:
            logger.error(f"读取响应失败: {e}")

    async def _handle_response(self, response: Dict[str, Any]) -> None:
        """处理响应"""
        if "id" in response:
            request_id = response["id"]
            if request_id in self._pending_requests:
                future = self._pending_requests.pop(request_id)
                future.set_result(response)

    async def _send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """发送 JSON-RPC 请求"""
        if not self._process or not self._process.stdin:
            raise RuntimeError("MCP Server 未连接")

        self._request_id += 1
        request_id = self._request_id

        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        }

        # 创建等待 Future
        future = asyncio.Future()
        self._pending_requests[request_id] = future

        # 发送请求
        message = json.dumps(request) + "\n"
        self._process.stdin.write(message.encode("utf-8"))
        await self._process.stdin.drain()

        # 等待响应
        try:
            response = await asyncio.wait_for(future, timeout=self.config.env.get("timeout", 30))
            return response
        except asyncio.TimeoutError:
            self._pending_requests.pop(request_id, None)
            raise TimeoutError(f"请求超时: {method}")

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
