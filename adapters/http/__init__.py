"""
HTTP 适配器模块

支持调用 REST API，遵循 OpenAPI 3.0 规范。

特性：
- OpenAPI 3.0 规范解析
- 多种认证方式（Bearer, API Key, Basic, OAuth2）
- 自动重试和错误处理
- 端点发现和工具清单生成

参考项目：
- encode/httpx
- OpenAPI 3.0 Specification
"""

from .base import HTTPAdapter
from .client import (
    HTTPClient,
    AuthConfig,
    AuthType,
    RetryConfig,
    RequestConfig,
    Response,
)
from .openapi_parser import (
    OpenAPIParser,
    OpenAPISpec,
    APIEndpoint,
    APIParameter,
    APIRequestBody,
    APIResponse,
    parse_openapi,
)


__all__ = [
    # 适配器
    "HTTPAdapter",
    # 客户端
    "HTTPClient",
    "AuthConfig",
    "AuthType",
    "RetryConfig",
    "RequestConfig",
    "Response",
    # OpenAPI 解析器
    "OpenAPIParser",
    "OpenAPISpec",
    "APIEndpoint",
    "APIParameter",
    "APIRequestBody",
    "APIResponse",
    "parse_openapi",
]
