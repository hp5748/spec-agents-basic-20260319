"""
HTTP Adapter 模块

提供 REST API 调用能力，包括：
- 客户端：异步 HTTP 客户端
- 配置：YAML 配置加载
"""

from .client import HTTPAdapter, HTTPEndpoint, create_http_adapter
from .config import HTTPConfigLoader, load_http_adapter


__all__ = [
    "HTTPAdapter",
    "HTTPEndpoint",
    "create_http_adapter",
    "HTTPConfigLoader",
    "load_http_adapter",
]
