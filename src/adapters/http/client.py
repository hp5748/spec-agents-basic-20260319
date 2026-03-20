"""
HTTP Adapter - REST API 客户端

提供通用的 HTTP 调用能力，支持：
- GET/POST/PUT/DELETE 等 HTTP 方法
- API Key/Bearer Token 认证
- URL 模板替换
- 请求头和请求体处理
- 连接池管理
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

import httpx

from ..core.base import BaseAdapter
from ..core.types import (
    AdapterConfig,
    AdapterType,
    ToolRequest,
    ToolResponse,
    AdapterHealthStatus,
)


logger = logging.getLogger(__name__)


class HTTPEndpoint:
    """HTTP 端点配置"""

    def __init__(
        self,
        name: str,
        method: str,
        path: str,
        description: Optional[str] = None,
        auth_type: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0,
    ):
        self.name = name
        self.method = method.upper()
        self.path = path
        self.description = description or f"HTTP {method} {path}"
        self.auth_type = auth_type
        self.headers = headers or {}
        self.timeout = timeout

        # 从路径提取参数
        self.path_params = self._extract_path_params()

    def _extract_path_params(self) -> List[str]:
        """从路径提取参数（如 {id}）"""
        import re

        return re.findall(r"\{(\w+)\}", self.path)

    def get_url(self, base_url: str, parameters: Dict[str, Any]) -> str:
        """构建完整 URL"""
        # 替换路径参数
        path = self.path
        for param in self.path_params:
            if param in parameters:
                path = path.replace(f"{{{param}}}", str(parameters[param]))

        return urljoin(base_url, path)


class HTTPAdapter(BaseAdapter):
    """
    HTTP 适配器

    支持调用外部 REST API，包括：
    - 配置驱动的端点管理
    - 多种认证方式
    - 连接池管理
    - 错误重试
    """

    def __init__(
        self,
        config: Optional[AdapterConfig] = None,
        base_url: Optional[str] = None,
        auth_config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            config
            or AdapterConfig(
                type=AdapterType.HTTP,
                name="http",
                metadata={"base_url": base_url, "auth": auth_config} if base_url else {},
            )
        )
        self.base_url = base_url or self.config.metadata.get("base_url", "")
        self.auth_config = auth_config or self.config.metadata.get("auth", {})

        self._endpoints: Dict[str, HTTPEndpoint] = {}
        self._client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> None:
        """初始化适配器"""
        logger.info(f"初始化 HTTP 适配器: {self.config.name}")

        # 创建 HTTP 客户端
        timeout = httpx.Timeout(self.config.metadata.get("timeout", 30.0))
        limits = httpx.Limits(
            max_connections=self.config.metadata.get("max_connections", 100),
            max_keepalive_connections=self.config.metadata.get("max_keepalive", 20),
        )

        self._client = httpx.AsyncClient(timeout=timeout, limits=limits)
        self._initialized = True

    async def shutdown(self) -> None:
        """关闭适配器"""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._initialized = False
        logger.info(f"关闭 HTTP 适配器: {self.config.name}")

    async def execute(self, request: ToolRequest) -> ToolResponse:
        """执行工具调用"""
        start_time = asyncio.get_event_loop().time()

        try:
            endpoint = self._endpoints.get(request.tool_name)
            if not endpoint:
                return ToolResponse(
                    tool_name=request.tool_name,
                    success=False,
                    error=f"端点 {request.tool_name} 不存在",
                )

            # 构建 HTTP 请求
            url = endpoint.get_url(self.base_url, request.parameters)
            method = endpoint.method
            headers = {**endpoint.headers, **request.metadata.get("headers", {})}

            # 准备请求参数
            params = {}
            body = None

            # 分离路径参数、查询参数和请求体
            for key, value in request.parameters.items():
                if key not in endpoint.path_params:
                    if method in ["POST", "PUT", "PATCH"]:
                        if body is None:
                            body = {}
                        body[key] = value
                    else:
                        params[key] = value

            # 添加认证
            await self._add_auth(headers, params, endpoint.auth_type)

            # 发送请求
            response = await self._client.request(
                method=method,
                url=url,
                params=params if params else None,
                json=body if body else None,
                headers=headers,
            )

            # 检查响应
            response.raise_for_status()

            # 解析响应
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                data = response.json()
            else:
                data = response.text

            return ToolResponse(
                tool_name=request.tool_name,
                success=True,
                data=data,
                metadata={
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "execution_time": asyncio.get_event_loop().time() - start_time,
                },
            )

        except httpx.HTTPStatusError as e:
            return ToolResponse(
                tool_name=request.tool_name,
                success=False,
                error=f"HTTP 错误: {e.response.status_code}",
                metadata={"status_code": e.response.status_code, "response": e.response.text},
            )
        except httpx.RequestError as e:
            return ToolResponse(
                tool_name=request.tool_name,
                success=False,
                error=f"请求失败: {str(e)}",
            )
        except Exception as e:
            return ToolResponse(
                tool_name=request.tool_name,
                success=False,
                error=str(e),
            )

    async def _add_auth(
        self, headers: Dict[str, str], params: Dict[str, Any], auth_type: Optional[str]
    ) -> None:
        """添加认证信息"""
        if not auth_type:
            auth_type = self.auth_config.get("type")

        if auth_type == "bearer":
            token = self.auth_config.get("token")
            if token:
                headers["Authorization"] = f"Bearer {token}"
        elif auth_type == "api_key":
            key = self.auth_config.get("key")
            value = self.auth_config.get("value")
            if key and value:
                headers[key] = value
        elif auth_type == "basic":
            username = self.auth_config.get("username")
            password = self.auth_config.get("password")
            if username and password:
                import base64

                credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers["Authorization"] = f"Basic {credentials}"

    async def health_check(self) -> AdapterHealthStatus:
        """健康检查"""
        healthy = self._initialized and self._client is not None
        return AdapterHealthStatus(
            healthy=healthy,
            endpoint_count=len(self._endpoints),
            base_url=self.base_url,
        )

    def register_endpoint(self, endpoint: HTTPEndpoint) -> None:
        """注册端点"""
        self._endpoints[endpoint.name] = endpoint
        logger.info(f"注册 HTTP 端点: {endpoint.name}")

    def unregister_endpoint(self, name: str) -> None:
        """注销端点"""
        if name in self._endpoints:
            del self._endpoints[name]
            logger.info(f"注销 HTTP 端点: {name}")

    def get_endpoint(self, name: str) -> Optional[HTTPEndpoint]:
        """获取端点"""
        return self._endpoints.get(name)

    def list_endpoints(self) -> List[str]:
        """列出所有端点"""
        return list(self._endpoints.keys())

    def get_endpoint_schema(self, name: str) -> Optional[Dict[str, Any]]:
        """获取端点的 OpenAPI Schema"""
        endpoint = self._endpoints.get(name)
        if not endpoint:
            return None

        return {
            "name": endpoint.name,
            "description": endpoint.description,
            "parameters": {
                "type": "object",
                "properties": {
                    param: {"type": "string"} for param in endpoint.path_params
                },
                "required": endpoint.path_params,
            },
        }

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """获取所有端点的 Schema"""
        return [
            self.get_endpoint_schema(name)
            for name in self._endpoints.keys()
            if self.get_endpoint_schema(name) is not None
        ]


async def create_http_adapter(
    name: str,
    base_url: str,
    endpoints: List[Dict[str, Any]],
    auth_config: Optional[Dict[str, Any]] = None,
) -> HTTPAdapter:
    """
    便捷函数：创建 HTTP 适配器

    Args:
        name: 适配器名称
        base_url: 基础 URL
        endpoints: 端点配置列表
        auth_config: 认证配置

    Returns:
        初始化后的 HTTP 适配器
    """
    adapter = HTTPAdapter(
        config=AdapterConfig(type=AdapterType.HTTP, name=name),
        base_url=base_url,
        auth_config=auth_config,
    )

    # 注册端点
    for ep_config in endpoints:
        endpoint = HTTPEndpoint(
            name=ep_config["name"],
            method=ep_config.get("method", "GET"),
            path=ep_config["path"],
            description=ep_config.get("description"),
            auth_type=ep_config.get("auth_type"),
            headers=ep_config.get("headers"),
            timeout=ep_config.get("timeout", 30.0),
        )
        adapter.register_endpoint(endpoint)

    await adapter.initialize()
    return adapter
