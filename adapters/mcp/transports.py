"""
MCP 传输层

支持多种 MCP 传输方式：
- stdio: 标准输入/输出
- sse: Server-Sent Events (HTTP)
- streamable-http: 可流式 HTTP

参考：
- Model Context Protocol Specification
- modelcontextprotocol/servers
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, AsyncIterator
from dataclasses import dataclass, field
import asyncio
import json
import logging
import uuid


logger = logging.getLogger(__name__)


@dataclass
class MCPMessage:
    """MCP 消息"""
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = {"jsonrpc": self.jsonrpc}
        if self.id is not None:
            data["id"] = self.id
        if self.method:
            data["method"] = self.method
        if self.params is not None:
            data["params"] = self.params
        if self.result is not None:
            data["result"] = self.result
        if self.error is not None:
            data["error"] = self.error
        return data

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPMessage":
        """从字典创建"""
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data.get("id"),
            method=data.get("method"),
            params=data.get("params"),
            result=data.get("result"),
            error=data.get("error"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "MCPMessage":
        """从 JSON 字符串创建"""
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def request(cls, method: str, params: Optional[Dict] = None, msg_id: Optional[int] = None) -> "MCPMessage":
        """创建请求消息"""
        return cls(method=method, params=params, id=msg_id)

    @classmethod
    def response(cls, result: Any, msg_id: int) -> "MCPMessage":
        """创建响应消息"""
        return cls(result=result, id=msg_id)

    @classmethod
    def error_response(cls, code: int, message: str, msg_id: Optional[int] = None) -> "MCPMessage":
        """创建错误响应"""
        return cls(
            error={"code": code, "message": message},
            id=msg_id
        )

    @classmethod
    def notification(cls, method: str, params: Optional[Dict] = None) -> "MCPMessage":
        """创建通知消息（无 id）"""
        return cls(method=method, params=params)


class BaseTransport(ABC):
    """
    传输层基类

    所有 MCP 传输方式必须实现此接口。
    """

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self._request_id = 0
        self._connected = False

    @property
    def connected(self) -> bool:
        """是否已连接"""
        return self._connected

    @abstractmethod
    async def connect(self) -> bool:
        """建立连接"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """断开连接"""
        pass

    @abstractmethod
    async def send(self, message: MCPMessage) -> None:
        """发送消息"""
        pass

    @abstractmethod
    async def receive(self) -> MCPMessage:
        """接收消息"""
        pass

    async def request(self, method: str, params: Optional[Dict] = None) -> MCPMessage:
        """
        发送请求并等待响应

        Args:
            method: 方法名
            params: 参数

        Returns:
            MCPMessage: 响应消息
        """
        self._request_id += 1
        message = MCPMessage.request(method, params, self._request_id)
        await self.send(message)
        return await self.receive()

    async def notify(self, method: str, params: Optional[Dict] = None) -> None:
        """
        发送通知（不等待响应）

        Args:
            method: 方法名
            params: 参数
        """
        message = MCPMessage.notification(method, params)
        await self.send(message)


class StdioTransport(BaseTransport):
    """
    stdio 传输

    通过标准输入/输出与 MCP Server 通信。
    """

    def __init__(self, server_path: str, args: list = None, env: dict = None, timeout: float = 30.0):
        """
        初始化 stdio 传输

        Args:
            server_path: MCP Server 脚本路径
            args: 命令行参数
            env: 环境变量
            timeout: 超时时间
        """
        super().__init__(timeout)
        self.server_path = server_path
        self.args = args or []
        self.env = env or {}
        self._process: Optional[asyncio.subprocess.Process] = None
        self._reader_lock = asyncio.Lock()
        self._writer_lock = asyncio.Lock()

    async def connect(self) -> bool:
        """启动 MCP Server 进程"""
        if self._connected:
            return True

        try:
            # 构建环境变量
            import os
            process_env = dict(os.environ)
            process_env.update(self.env)

            # 启动进程
            self._process = await asyncio.create_subprocess_exec(
                "python", self.server_path, *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=process_env,
            )

            self._connected = True
            logger.info(f"stdio 传输已连接: {self.server_path}")
            return True

        except Exception as e:
            logger.error(f"stdio 传输连接失败: {e}")
            return False

    async def disconnect(self) -> None:
        """终止 MCP Server 进程"""
        if not self._connected:
            return

        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self._process.kill()
                await self._process.wait()
            except Exception as e:
                logger.error(f"终止进程失败: {e}")
            finally:
                self._process = None

        self._connected = False
        logger.info("stdio 传输已断开")

    async def send(self, message: MCPMessage) -> None:
        """发送消息到 stdin"""
        if not self._process or not self._process.stdin:
            raise RuntimeError("未连接到 MCP Server")

        async with self._writer_lock:
            json_str = message.to_json() + "\n"
            self._process.stdin.write(json_str.encode())
            await self._process.stdin.drain()

    async def receive(self) -> MCPMessage:
        """从 stdout 接收消息"""
        if not self._process or not self._process.stdout:
            raise RuntimeError("未连接到 MCP Server")

        async with self._reader_lock:
            line = await asyncio.wait_for(
                self._process.stdout.readline(),
                timeout=self.timeout
            )
            return MCPMessage.from_json(line.decode().strip())


class SSETransport(BaseTransport):
    """
    SSE (Server-Sent Events) 传输

    通过 HTTP SSE 与 MCP Server 通信。
    """

    def __init__(
        self,
        server_url: str,
        headers: dict = None,
        timeout: float = 30.0,
        reconnect_interval: float = 5.0,
    ):
        """
        初始化 SSE 传输

        Args:
            server_url: MCP Server URL
            headers: 请求头
            timeout: 超时时间
            reconnect_interval: 重连间隔
        """
        super().__init__(timeout)
        self.server_url = server_url
        self.headers = headers or {}
        self.reconnect_interval = reconnect_interval
        self._client = None
        self._response = None
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._receive_task: Optional[asyncio.Task] = None

    async def connect(self) -> bool:
        """建立 SSE 连接"""
        if self._connected:
            return True

        try:
            import httpx

            self._client = httpx.AsyncClient(timeout=self.timeout)
            self._response = await self._client.get(
                self.server_url,
                headers={**self.headers, "Accept": "text/event-stream"},
            )
            self._response.raise_for_status()

            # 启动接收任务
            self._receive_task = asyncio.create_task(self._receive_loop())

            self._connected = True
            logger.info(f"SSE 传输已连接: {self.server_url}")
            return True

        except Exception as e:
            logger.error(f"SSE 传输连接失败: {e}")
            return False

    async def _receive_loop(self) -> None:
        """SSE 接收循环"""
        try:
            async for line in self._response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data:
                        try:
                            message = MCPMessage.from_json(data)
                            await self._message_queue.put(message)
                        except json.JSONDecodeError:
                            logger.warning(f"无效的 JSON 数据: {data}")
        except Exception as e:
            logger.error(f"SSE 接收循环异常: {e}")
            self._connected = False

    async def disconnect(self) -> None:
        """断开 SSE 连接"""
        if not self._connected:
            return

        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        if self._response:
            await self._response.aclose()
            self._response = None

        if self._client:
            await self._client.aclose()
            self._client = None

        self._connected = False
        logger.info("SSE 传输已断开")

    async def send(self, message: MCPMessage) -> None:
        """通过 HTTP POST 发送消息"""
        if not self._client:
            raise RuntimeError("未连接到 MCP Server")

        # SSE 是单向的，发送通过 POST
        post_url = self.server_url.replace("/sse", "/message")
        response = await self._client.post(
            post_url,
            json=message.to_dict(),
            headers=self.headers,
        )
        response.raise_for_status()

    async def receive(self) -> MCPMessage:
        """从消息队列接收消息"""
        return await asyncio.wait_for(
            self._message_queue.get(),
            timeout=self.timeout
        )


class StreamableHTTPTransport(BaseTransport):
    """
    可流式 HTTP 传输

    支持 MCP 的 streamable-http 传输方式。
    """

    def __init__(
        self,
        server_url: str,
        headers: dict = None,
        timeout: float = 30.0,
    ):
        """
        初始化 streamable-http 传输

        Args:
            server_url: MCP Server URL
            headers: 请求头
            timeout: 超时时间
        """
        super().__init__(timeout)
        self.server_url = server_url.rstrip("/")
        self.headers = headers or {}
        self._client = None
        self._session_id: Optional[str] = None

    async def connect(self) -> bool:
        """建立 HTTP 连接"""
        if self._connected:
            return True

        try:
            import httpx
            self._client = httpx.AsyncClient(timeout=self.timeout)
            self._session_id = str(uuid.uuid4())
            self._connected = True
            logger.info(f"streamable-http 传输已连接: {self.server_url}")
            return True

        except Exception as e:
            logger.error(f"streamable-http 传输连接失败: {e}")
            return False

    async def disconnect(self) -> None:
        """断开连接"""
        if self._client:
            await self._client.aclose()
            self._client = None

        self._connected = False
        logger.info("streamable-http 传输已断开")

    async def send(self, message: MCPMessage) -> None:
        """发送消息（streamable-http 中 send/receive 是一体的）"""
        if not self._client:
            raise RuntimeError("未连接到 MCP Server")

        headers = {
            **self.headers,
            "Content-Type": "application/json",
        }
        if self._session_id:
            headers["X-Session-Id"] = self._session_id

        response = await self._client.post(
            f"{self.server_url}/mcp",
            json=message.to_dict(),
            headers=headers,
        )
        response.raise_for_status()

        # 在 streamable-http 中，响应直接返回
        if response.content:
            data = response.json()
            if "result" in data or "error" in data:
                self._last_response = MCPMessage.from_dict(data)

    async def receive(self) -> MCPMessage:
        """接收消息"""
        if hasattr(self, "_last_response") and self._last_response:
            response = self._last_response
            self._last_response = None
            return response

        # 等待响应
        await asyncio.sleep(0.1)
        raise RuntimeError("没有可用的响应")


def create_transport(
    transport_type: str,
    **kwargs
) -> BaseTransport:
    """
    工厂函数：创建传输层

    Args:
        transport_type: 传输类型 (stdio / sse / streamable-http)
        **kwargs: 传输层参数

    Returns:
        BaseTransport: 传输层实例
    """
    transport_map = {
        "stdio": StdioTransport,
        "sse": SSETransport,
        "streamable-http": StreamableHTTPTransport,
        "streamableHttp": StreamableHTTPTransport,
    }

    transport_class = transport_map.get(transport_type)
    if not transport_class:
        raise ValueError(f"不支持的传输类型: {transport_type}")

    return transport_class(**kwargs)
