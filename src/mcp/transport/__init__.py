"""
MCP 传输层

支持多种传输方式：
- STDIO: 本地进程通信
- HTTP: 远程 HTTP 服务
- SSE: 服务器推送事件
"""

from .stdio import STDIOTransport
from .http import HTTPTransport

__all__ = [
    "STDIOTransport",
    "HTTPTransport",
]
