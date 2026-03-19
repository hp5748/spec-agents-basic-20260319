"""
MCP 客户端

增强的 MCP 客户端，支持：
- 多种传输方式（stdio, SSE, streamable-http）
- 工具调用
- 资源访问
- 提示词管理
- 采样请求

参考：
- Model Context Protocol Specification
- modelcontextprotocol/sdk-python
"""

from typing import Any, Dict, List, Optional, Callable, AsyncIterator
from dataclasses import dataclass, field
import asyncio
import logging
from enum import Enum

from .transports import (
    BaseTransport,
    StdioTransport,
    SSETransport,
    StreamableHTTPTransport,
    MCPMessage,
    create_transport,
)


logger = logging.getLogger(__name__)


class MCPCapability(Enum):
    """MCP 能力"""
    TOOLS = "tools"
    RESOURCES = "resources"
    PROMPTS = "prompts"
    SAMPLING = "sampling"
    LOGGING = "logging"


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    input_schema: Dict[str, Any]


@dataclass
class ResourceDefinition:
    """资源定义"""
    uri: str
    name: str
    description: str = ""
    mime_type: str = ""


@dataclass
class PromptDefinition:
    """提示词定义"""
    name: str
    description: str
    arguments: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ServerInfo:
    """服务器信息"""
    name: str
    version: str
    protocol_version: str
    capabilities: List[str] = field(default_factory=list)


class MCPClient:
    """
    MCP 客户端

    支持 Model Context Protocol 的完整功能。

    使用方式：
        client = MCPClient(
            transport_type="stdio",
            transport_config={"server_path": "adapters/mcp/servers/fetch/server.py"}
        )
        await client.connect()

        # 列出工具
        tools = await client.list_tools()

        # 调用工具
        result = await client.call_tool("fetch", {"url": "https://example.com"})

        # 访问资源
        resources = await client.list_resources()
        content = await client.read_resource("file:///path/to/file")
    """

    PROTOCOL_VERSION = "2024-11-05"
    CLIENT_INFO = {"name": "skill-mcp-client", "version": "1.0.0"}

    def __init__(
        self,
        transport_type: str = "stdio",
        transport_config: Dict[str, Any] = None,
        timeout: float = 30.0,
        on_notification: Optional[Callable[[MCPMessage], None]] = None,
    ):
        """
        初始化 MCP 客户端

        Args:
            transport_type: 传输类型 (stdio / sse / streamable-http)
            transport_config: 传输配置
            timeout: 超时时间
            on_notification: 通知回调函数
        """
        self.transport_type = transport_type
        self.transport_config = transport_config or {}
        self.timeout = timeout
        self.on_notification = on_notification

        self._transport: Optional[BaseTransport] = None
        self._server_info: Optional[ServerInfo] = None
        self._capabilities: Dict[str, bool] = {}
        self._initialized = False

    @property
    def connected(self) -> bool:
        """是否已连接"""
        return self._transport is not None and self._transport.connected

    @property
    def server_info(self) -> Optional[ServerInfo]:
        """服务器信息"""
        return self._server_info

    @property
    def capabilities(self) -> Dict[str, bool]:
        """服务器能力"""
        return self._capabilities

    async def connect(self) -> bool:
        """连接到 MCP Server"""
        if self.connected:
            return True

        try:
            # 创建传输层
            self._transport = create_transport(
                self.transport_type,
                timeout=self.timeout,
                **self.transport_config
            )

            # 建立连接
            if not await self._transport.connect():
                return False

            # 发送初始化请求
            await self._initialize()

            self._initialized = True
            logger.info(f"MCP 客户端已连接: {self.transport_type}")
            return True

        except Exception as e:
            logger.error(f"MCP 客户端连接失败: {e}")
            return False

    async def _initialize(self) -> None:
        """发送初始化请求"""
        response = await self._transport.request(
            "initialize",
            {
                "protocolVersion": self.PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": self.CLIENT_INFO,
            }
        )

        if response.error:
            raise RuntimeError(f"初始化失败: {response.error}")

        result = response.result or {}
        self._server_info = ServerInfo(
            name=result.get("serverInfo", {}).get("name", "unknown"),
            version=result.get("serverInfo", {}).get("version", "unknown"),
            protocol_version=result.get("protocolVersion", ""),
            capabilities=list(result.get("capabilities", {}).keys()),
        )

        # 解析能力
        capabilities = result.get("capabilities", {})
        self._capabilities = {
            "tools": capabilities.get("tools", {}).get("supported", False),
            "resources": capabilities.get("resources", {}).get("supported", False),
            "prompts": capabilities.get("prompts", {}).get("supported", False),
            "sampling": capabilities.get("sampling", {}).get("supported", False),
            "logging": capabilities.get("logging", {}).get("supported", False),
        }

        # 发送 initialized 通知
        await self._transport.notify("notifications/initialized")

    # ========================================
    # 工具相关
    # ========================================

    async def list_tools(self) -> List[ToolDefinition]:
        """列出可用工具"""
        if not self._capabilities.get("tools"):
            return []

        response = await self._transport.request("tools/list", {})

        if response.error:
            logger.error(f"列出工具失败: {response.error}")
            return []

        tools = []
        for tool_data in response.result.get("tools", []):
            tools.append(ToolDefinition(
                name=tool_data.get("name", ""),
                description=tool_data.get("description", ""),
                input_schema=tool_data.get("inputSchema", {}),
            ))
        return tools

    async def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        调用工具

        Args:
            name: 工具名称
            arguments: 工具参数

        Returns:
            List[Dict]: 工具返回的内容列表
        """
        response = await self._transport.request(
            "tools/call",
            {"name": name, "arguments": arguments or {}}
        )

        if response.error:
            raise RuntimeError(f"工具调用失败: {response.error}")

        return response.result.get("content", [])

    # ========================================
    # 资源相关
    # ========================================

    async def list_resources(self) -> List[ResourceDefinition]:
        """列出可用资源"""
        if not self._capabilities.get("resources"):
            return []

        response = await self._transport.request("resources/list", {})

        if response.error:
            logger.error(f"列出资源失败: {response.error}")
            return []

        resources = []
        for res_data in response.result.get("resources", []):
            resources.append(ResourceDefinition(
                uri=res_data.get("uri", ""),
                name=res_data.get("name", ""),
                description=res_data.get("description", ""),
                mime_type=res_data.get("mimeType", ""),
            ))
        return resources

    async def read_resource(self, uri: str) -> List[Dict[str, Any]]:
        """
        读取资源

        Args:
            uri: 资源 URI

        Returns:
            List[Dict]: 资源内容列表
        """
        response = await self._transport.request(
            "resources/read",
            {"uri": uri}
        )

        if response.error:
            raise RuntimeError(f"读取资源失败: {response.error}")

        return response.result.get("contents", [])

    async def subscribe_resource(self, uri: str) -> bool:
        """订阅资源变更"""
        if not self._capabilities.get("resources"):
            return False

        response = await self._transport.request(
            "resources/subscribe",
            {"uri": uri}
        )

        return not response.error

    async def unsubscribe_resource(self, uri: str) -> bool:
        """取消订阅资源"""
        if not self._capabilities.get("resources"):
            return False

        response = await self._transport.request(
            "resources/unsubscribe",
            {"uri": uri}
        )

        return not response.error

    # ========================================
    # 提示词相关
    # ========================================

    async def list_prompts(self) -> List[PromptDefinition]:
        """列出可用提示词"""
        if not self._capabilities.get("prompts"):
            return []

        response = await self._transport.request("prompts/list", {})

        if response.error:
            logger.error(f"列出提示词失败: {response.error}")
            return []

        prompts = []
        for prompt_data in response.result.get("prompts", []):
            prompts.append(PromptDefinition(
                name=prompt_data.get("name", ""),
                description=prompt_data.get("description", ""),
                arguments=prompt_data.get("arguments", []),
            ))
        return prompts

    async def get_prompt(
        self,
        name: str,
        arguments: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        获取提示词

        Args:
            name: 提示词名称
            arguments: 提示词参数

        Returns:
            Dict: 提示词内容
        """
        response = await self._transport.request(
            "prompts/get",
            {"name": name, "arguments": arguments or {}}
        )

        if response.error:
            raise RuntimeError(f"获取提示词失败: {response.error}")

        return response.result

    # ========================================
    # 采样相关
    # ========================================

    async def create_message(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int = 1000,
        **options
    ) -> Dict[str, Any]:
        """
        创建采样消息

        Args:
            messages: 消息列表
            max_tokens: 最大 token 数
            **options: 其他选项

        Returns:
            Dict: 采样结果
        """
        if not self._capabilities.get("sampling"):
            raise RuntimeError("服务器不支持采样")

        response = await self._transport.request(
            "sampling/createMessage",
            {
                "messages": messages,
                "maxTokens": max_tokens,
                **options
            }
        )

        if response.error:
            raise RuntimeError(f"采样失败: {response.error}")

        return response.result

    # ========================================
    # 日志相关
    # ========================================

    async def set_log_level(self, level: str) -> bool:
        """设置日志级别"""
        if not self._capabilities.get("logging"):
            return False

        response = await self._transport.request(
            "logging/setLevel",
            {"level": level}
        )

        return not response.error

    # ========================================
    # 生命周期
    # ========================================

    async def disconnect(self) -> None:
        """断开连接"""
        if self._transport:
            await self._transport.disconnect()
            self._transport = None

        self._initialized = False
        self._server_info = None
        self._capabilities.clear()

    async def health_check(self) -> bool:
        """健康检查"""
        return self.connected and self._initialized

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.disconnect()
