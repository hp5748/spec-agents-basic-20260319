"""
MCP 适配器模块

支持 Model Context Protocol (MCP)，连接 MCP Server。

特性：
- 多种传输方式（stdio, SSE, streamable-http）
- 工具调用
- 资源访问和订阅
- 提示词管理
- 采样请求

参考项目：
- modelcontextprotocol/servers (官方 MCP 服务器)
- MCP Specification
"""

from .base import MCPAdapter
from .client import (
    MCPClient,
    MCPCapability,
    ToolDefinition,
    ResourceDefinition,
    PromptDefinition,
    ServerInfo,
)
from .transports import (
    BaseTransport,
    StdioTransport,
    SSETransport,
    StreamableHTTPTransport,
    MCPMessage,
    create_transport,
)


__all__ = [
    # 适配器
    "MCPAdapter",
    # 客户端
    "MCPClient",
    "MCPCapability",
    "ToolDefinition",
    "ResourceDefinition",
    "PromptDefinition",
    "ServerInfo",
    # 传输层
    "BaseTransport",
    "StdioTransport",
    "SSETransport",
    "StreamableHTTPTransport",
    "MCPMessage",
    "create_transport",
]
