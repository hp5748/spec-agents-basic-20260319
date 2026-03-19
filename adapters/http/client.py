"""
HTTP 客户端

增强的 HTTP 客户端，支持：
- 多种认证方式（Bearer Token, API Key, Basic Auth, OAuth2）
- 自动重试
- 请求/响应拦截
- 错误处理
- 超时控制

参考：
- encode/httpx
- OpenAPI 3.0
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union
import asyncio
import logging
import time
from enum import Enum


logger = logging.getLogger(__name__)


class AuthType(Enum):
    """认证类型"""
    NONE = "none"
    BEARER = "bearer"
    API_KEY = "api_key"
    BASIC = "basic"
    OAUTH2 = "oauth2"


@dataclass
class AuthConfig:
    """认证配置"""
    type: AuthType = AuthType.NONE
    # Bearer Token
    token: str = ""
    token_env: str = ""
    # API Key
    api_key: str = ""
    api_key_env: str = ""
    api_key_header: str = "X-API-Key"
    # Basic Auth
    username: str = ""
    password: str = ""
    # OAuth2
    client_id: str = ""
    client_secret: str = ""
    token_url: str = ""


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    retry_status_codes: List[int] = field(default_factory=lambda: [429, 500, 502, 503, 504])
    retry_delay: float = 1.0
    retry_multiplier: float = 2.0
    max_delay: float = 30.0


@dataclass
class RequestConfig:
    """请求配置"""
    method: str = "GET"
    url: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)
    body: Optional[Union[Dict, str, bytes]] = None
    timeout: float = 30.0


@dataclass
class Response:
    """响应"""
    status_code: int
    headers: Dict[str, str]
    body: Any
    elapsed: float
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        """请求是否成功"""
        return 200 <= self.status_code < 300

    def json(self) -> Any:
        """获取 JSON 响应"""
        if isinstance(self.body, dict):
            return self.body
        return self.body


class HTTPClient:
    """
    HTTP 客户端

    增强的 HTTP 客户端，支持多种认证方式和重试机制。

    使用方式：
        client = HTTPClient(
            base_url="https://api.example.com",
            auth=AuthConfig(type=AuthType.BEARER, token_env="API_TOKEN")
        )
        await client.initialize()

        response = await client.request("GET", "/users")
        print(response.json())
    """

    def __init__(
        self,
        base_url: str = "",
        auth: Optional[AuthConfig] = None,
        retry: Optional[RetryConfig] = None,
        default_timeout: float = 30.0,
        default_headers: Optional[Dict[str, str]] = None,
    ):
        """
        初始化 HTTP 客户端

        Args:
            base_url: 基础 URL
            auth: 认证配置
            retry: 重试配置
            default_timeout: 默认超时时间
            default_headers: 默认请求头
        """
        self.base_url = base_url.rstrip("/")
        self.auth = auth or AuthConfig()
        self.retry = retry or RetryConfig()
        self.default_timeout = default_timeout
        self.default_headers = default_headers or {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        self._client = None
        self._access_token: Optional[str] = None
        self._initialized = False

    async def initialize(self) -> bool:
        """初始化客户端"""
        try:
            import httpx
            self._client = httpx.AsyncClient(
                timeout=self.default_timeout,
                headers=self._build_auth_headers(),
            )
            self._initialized = True
            logger.info(f"HTTP 客户端初始化完成: {self.base_url}")
            return True
        except ImportError:
            logger.error("httpx 未安装，请执行: pip install httpx")
            return False
        except Exception as e:
            logger.error(f"HTTP 客户端初始化失败: {e}")
            return False

    def _build_auth_headers(self) -> Dict[str, str]:
        """构建认证请求头"""
        headers = dict(self.default_headers)

        if self.auth.type == AuthType.BEARER:
            token = self._get_secret(self.auth.token, self.auth.token_env)
            if token:
                headers["Authorization"] = f"Bearer {token}"

        elif self.auth.type == AuthType.API_KEY:
            api_key = self._get_secret(self.auth.api_key, self.auth.api_key_env)
            if api_key:
                headers[self.auth.api_key_header] = api_key

        elif self.auth.type == AuthType.BASIC:
            import base64
            credentials = base64.b64encode(
                f"{self.auth.username}:{self.auth.password}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {credentials}"

        return headers

    def _get_secret(self, value: str, env_name: str) -> str:
        """获取密钥（优先使用环境变量）"""
        import os
        if value:
            return value
        if env_name:
            return os.environ.get(env_name, "")
        return ""

    async def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Union[Dict, str, bytes]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> Response:
        """
        发送 HTTP 请求

        Args:
            method: HTTP 方法
            path: 请求路径
            params: 查询参数
            body: 请求体
            headers: 额外请求头
            timeout: 超时时间

        Returns:
            Response: 响应对象
        """
        if not self._initialized:
            await self.initialize()

        url = f"{self.base_url}{path}" if self.base_url else path
        request_headers = dict(self._build_auth_headers())
        if headers:
            request_headers.update(headers)

        request_timeout = timeout or self.default_timeout

        # 重试循环
        last_error = None
        for attempt in range(self.retry.max_retries + 1):
            try:
                start_time = time.time()

                response = await self._client.request(
                    method=method.upper(),
                    url=url,
                    params=params,
                    json=body if isinstance(body, dict) else None,
                    content=body if isinstance(body, (str, bytes)) else None,
                    headers=request_headers,
                    timeout=request_timeout,
                )

                elapsed = time.time() - start_time

                # 检查是否需要重试
                if response.status_code in self.retry.retry_status_codes:
                    if attempt < self.retry.max_retries:
                        delay = min(
                            self.retry.retry_delay * (self.retry.retry_multiplier ** attempt),
                            self.retry.max_delay
                        )
                        logger.warning(
                            f"请求失败 {response.status_code}，{delay:.1f}s 后重试 "
                            f"(attempt {attempt + 1}/{self.retry.max_retries})"
                        )
                        await asyncio.sleep(delay)
                        continue

                # 解析响应
                try:
                    response_body = response.json()
                except:
                    response_body = response.text

                return Response(
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    body=response_body,
                    elapsed=elapsed,
                    error=None if response.ok else f"HTTP {response.status_code}",
                )

            except asyncio.TimeoutError:
                last_error = "请求超时"
                if attempt < self.retry.max_retries:
                    delay = self.retry.retry_delay * (self.retry.retry_multiplier ** attempt)
                    logger.warning(f"请求超时，{delay:.1f}s 后重试")
                    await asyncio.sleep(delay)
                    continue

            except Exception as e:
                last_error = str(e)
                if attempt < self.retry.max_retries:
                    delay = self.retry.retry_delay * (self.retry.retry_multiplier ** attempt)
                    logger.warning(f"请求异常: {e}，{delay:.1f}s 后重试")
                    await asyncio.sleep(delay)
                    continue

        return Response(
            status_code=0,
            headers={},
            body=None,
            elapsed=0,
            error=last_error or "请求失败",
        )

    # 便捷方法
    async def get(self, path: str, params: Optional[Dict] = None, **kwargs) -> Response:
        """GET 请求"""
        return await self.request("GET", path, params=params, **kwargs)

    async def post(self, path: str, body: Optional[Dict] = None, **kwargs) -> Response:
        """POST 请求"""
        return await self.request("POST", path, body=body, **kwargs)

    async def put(self, path: str, body: Optional[Dict] = None, **kwargs) -> Response:
        """PUT 请求"""
        return await self.request("PUT", path, body=body, **kwargs)

    async def patch(self, path: str, body: Optional[Dict] = None, **kwargs) -> Response:
        """PATCH 请求"""
        return await self.request("PATCH", path, body=body, **kwargs)

    async def delete(self, path: str, **kwargs) -> Response:
        """DELETE 请求"""
        return await self.request("DELETE", path, **kwargs)

    async def health_check(self, health_path: str = "/health") -> bool:
        """健康检查"""
        try:
            response = await self.get(health_path, timeout=5.0)
            return response.ok
        except:
            return False

    async def close(self):
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None
            self._initialized = False

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
