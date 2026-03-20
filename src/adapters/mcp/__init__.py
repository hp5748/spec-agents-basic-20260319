"""
MCP Adapter 模块

提供 MCP (Model Context Protocol) 适配器实现，支持：
- STDIO 传输（本地进程）
- HTTP 传输（远程服务）
- 配置格式兼容（.claude/mcp.json 和 config/mcp.yaml）
- 工具自动注册到 ToolRegistry
"""

from .adapter import MCPAdapter
from .client import MCPClient
from .config import MCPConfigLoader, MCPServerConfig, MCPConfig

__all__ = [
    # 适配器
    "MCPAdapter",
    # 客户端
    "MCPClient",
    # 配置
    "MCPConfigLoader",
    "MCPServerConfig",
    "MCPConfig",
]
