"""
HTTP 适配器

支持调用 REST API，遵循 OpenAPI 3.0 规范。

特性：
- 支持 OpenAPI 3.0 规范解析
- 多种认证方式（Bearer, API Key, Basic, OAuth2）
- 自动重试
- 端点发现

参考项目：
- encode/httpx
- OpenAPI 3.0 Specification
"""

from typing import Any, Dict, List, Optional
import logging

from adapters.core.base_adapter import BaseAdapter
from adapters.core.types import AdapterConfig, AdapterResult, SkillContext

from .openapi_parser import OpenAPIParser, OpenAPISpec, APIEndpoint
from .client import HTTPClient, AuthConfig, AuthType, RetryConfig


logger = logging.getLogger(__name__)


class HTTPAdapter(BaseAdapter):
    """
    HTTP 适配器

    支持调用 REST API，遵循 OpenAPI 3.0 规范。

    配置示例:
        config = AdapterConfig(
            type=AdapterType.HTTP,
            name="order-api",
            metadata={
                "base_url": "https://api.example.com",
                "openapi_path": "adapters/http/specs/order-api.yaml",
                "auth": {
                    "type": "bearer",
                    "token_env": "ORDER_API_TOKEN"
                },
                "retry": {
                    "max_retries": 3,
                    "retry_status_codes": [429, 500, 502, 503, 504]
                }
            }
        )
    """

    def __init__(self, config: AdapterConfig):
        super().__init__(config)
        self._client: Optional[HTTPClient] = None
        self._openapi_spec: Optional[OpenAPISpec] = None
        self._endpoint_map: Dict[str, APIEndpoint] = {}

    async def initialize(self) -> bool:
        """
        初始化 HTTP 适配器

        - 加载 OpenAPI 规范
        - 初始化 HTTP 客户端
        - 构建端点映射
        """
        try:
            # 解析认证配置
            auth_config = self._parse_auth_config()

            # 解析重试配置
            retry_config = self._parse_retry_config()

            # 初始化 HTTP 客户端
            base_url = self.config.metadata.get("base_url", "")
            self._client = HTTPClient(
                base_url=base_url,
                auth=auth_config,
                retry=retry_config,
                default_timeout=self.config.timeout,
            )

            # 初始化客户端
            if not await self._client.initialize():
                return False

            # 加载 OpenAPI 规范
            openapi_path = self.config.metadata.get("openapi_path")
            if openapi_path:
                await self._load_openapi_spec(openapi_path)

            logger.info(f"HTTP 适配器初始化完成: {self.name}")
            return True

        except Exception as e:
            logger.error(f"HTTP 适配器初始化失败: {e}")
            return False

    def _parse_auth_config(self) -> AuthConfig:
        """解析认证配置"""
        auth_meta = self.config.metadata.get("auth", {})
        auth_type_str = auth_meta.get("type", "none")

        # 映射认证类型
        auth_type_map = {
            "none": AuthType.NONE,
            "bearer": AuthType.BEARER,
            "api_key": AuthType.API_KEY,
            "basic": AuthType.BASIC,
            "oauth2": AuthType.OAUTH2,
        }
        auth_type = auth_type_map.get(auth_type_str, AuthType.NONE)

        return AuthConfig(
            type=auth_type,
            token=auth_meta.get("token", ""),
            token_env=auth_meta.get("token_env", ""),
            api_key=auth_meta.get("api_key", ""),
            api_key_env=auth_meta.get("key_env", auth_meta.get("api_key_env", "")),
            api_key_header=auth_meta.get("header", "X-API-Key"),
            username=auth_meta.get("username", ""),
            password=auth_meta.get("password", ""),
            client_id=auth_meta.get("client_id", ""),
            client_secret=auth_meta.get("client_secret", ""),
            token_url=auth_meta.get("token_url", ""),
        )

    def _parse_retry_config(self) -> RetryConfig:
        """解析重试配置"""
        retry_meta = self.config.metadata.get("retry", {})
        return RetryConfig(
            max_retries=retry_meta.get("max_retries", 3),
            retry_status_codes=retry_meta.get("retry_status_codes", [429, 500, 502, 503, 504]),
            retry_delay=retry_meta.get("retry_delay", 1.0),
            retry_multiplier=retry_meta.get("retry_multiplier", 2.0),
            max_delay=retry_meta.get("max_delay", 30.0),
        )

    async def _load_openapi_spec(self, path: str) -> None:
        """加载 OpenAPI 规范"""
        try:
            parser = OpenAPIParser()
            self._openapi_spec = parser.parse(path)

            # 构建端点映射
            for endpoint in self._openapi_spec.endpoints:
                key = endpoint.operation_id or f"{endpoint.method}_{endpoint.path}"
                self._endpoint_map[key] = endpoint
                # 也用工具名映射
                self._endpoint_map[endpoint.get_tool_name()] = endpoint

            logger.info(
                f"加载 OpenAPI 规范: {self._openapi_spec.title} "
                f"({len(self._openapi_spec.endpoints)} 个端点)"
            )

        except Exception as e:
            logger.warning(f"加载 OpenAPI 规范失败: {e}")

    async def execute(
        self,
        context: SkillContext,
        input_data: Dict[str, Any]
    ) -> AdapterResult:
        """
        执行 HTTP 请求

        支持两种模式：
        1. 直接指定端点：input_data 包含 endpoint, method, params
        2. 通过 operation_id：input_data 包含 operation_id 和参数

        Args:
            context: 技能执行上下文
            input_data: 输入数据

        Returns:
            AdapterResult: 执行结果
        """
        if not self._client:
            return AdapterResult(
                success=False,
                data=None,
                error="HTTP 客户端未初始化"
            )

        # 确定请求配置
        endpoint = None
        method = None
        path_params = {}
        query_params = {}
        body = None

        # 模式 1：通过 operation_id 查找端点
        operation_id = input_data.get("operation_id")
        if operation_id and operation_id in self._endpoint_map:
            endpoint = self._endpoint_map[operation_id]
            method = endpoint.method

            # 构建路径（替换路径参数）
            path = endpoint.path
            for param in endpoint.parameters:
                if param.in_location == "path":
                    value = input_data.get(param.name, param.default)
                    if value is not None:
                        path = path.replace(f"{{{param.name}}}", str(value))
                    elif param.required:
                        return AdapterResult(
                            success=False,
                            data=None,
                            error=f"缺少必需的路径参数: {param.name}"
                        )
                elif param.in_location == "query":
                    value = input_data.get(param.name, param.default)
                    if value is not None:
                        query_params[param.name] = value

            # 请求体
            if endpoint.request_body and "body" in input_data:
                body = input_data["body"]

        # 模式 2：直接指定端点
        else:
            path = input_data.get("endpoint", self.config.metadata.get("endpoint", ""))
            method = input_data.get("method", "GET").upper()
            query_params = input_data.get("params", {})
            body = input_data.get("body")

        # 发送请求
        response = await self._client.request(
            method=method,
            path=path,
            params=query_params,
            body=body,
        )

        return AdapterResult(
            success=response.ok,
            data=response.body,
            error=response.error,
            metadata={
                "status_code": response.status_code,
                "elapsed": response.elapsed,
                "headers": response.headers,
            }
        )

    async def health_check(self) -> bool:
        """健康检查"""
        if not self._client:
            return False

        health_url = self.config.metadata.get("health_url", "/health")
        return await self._client.health_check(health_url)

    async def cleanup(self):
        """关闭 HTTP 客户端"""
        if self._client:
            await self._client.close()
            self._client = None

    def get_endpoints(self) -> List[Dict[str, Any]]:
        """获取所有可用端点"""
        if not self._openapi_spec:
            return []

        return [
            {
                "operation_id": ep.operation_id,
                "tool_name": ep.get_tool_name(),
                "method": ep.method.upper(),
                "path": ep.path,
                "summary": ep.summary,
                "description": ep.description,
                "deprecated": ep.deprecated,
            }
            for ep in self._openapi_spec.endpoints
            if not ep.deprecated
        ]

    def get_endpoint_schema(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """获取端点的输入 Schema"""
        if operation_id not in self._endpoint_map:
            return None

        endpoint = self._endpoint_map[operation_id]

        schema = {
            "type": "object",
            "properties": {},
            "required": [],
        }

        # 添加参数
        for param in endpoint.parameters:
            prop = param.schema.copy()
            if param.description:
                prop["description"] = param.description
            schema["properties"][param.name] = prop
            if param.required:
                schema["required"].append(param.name)

        # 添加请求体
        if endpoint.request_body:
            schema["properties"]["body"] = endpoint.request_body.schema
            if endpoint.request_body.required:
                schema["required"].append("body")

        return schema

    def get_tool_manifest(self) -> List[Dict[str, Any]]:
        """生成工具清单（用于 MCP 或 Agent）"""
        if not self._openapi_spec:
            return []

        parser = OpenAPIParser()
        return parser.generate_tool_manifest(self._openapi_spec)
