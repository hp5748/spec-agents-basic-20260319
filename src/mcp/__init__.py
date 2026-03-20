"""
MCP (Model Context Protocol) 模块

支持多种配置格式，按优先级加载：
- config/mcp.yaml (项目 YAML 配置，最高优先级)
- .claude/mcp.json (Claude Code 标准)
- ~/.claude.json (用户级配置)

传输方式：
- STDIO 传输（本地进程）
- HTTP 传输（远程服务）
- SSE 传输（服务器推送事件）
"""

from .config import MCPConfigLoader, MCPServerConfig, MCPConfig
from .client import MCPClient
from .tool_matcher import ToolMatcher, ToolInfo, MatchResult

__all__ = [
    # 配置
    "MCPConfigLoader",
    "MCPServerConfig",
    "MCPConfig",
    # 客户端
    "MCPClient",
    # 工具匹配
    "ToolMatcher",
    "ToolInfo",
    "MatchResult",
]
