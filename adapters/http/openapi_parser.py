"""
OpenAPI 解析器

解析 OpenAPI 3.0 规范文件，提取 API 端点信息。

支持：
- YAML / JSON 格式
- 自动提取端点、参数、响应
- 生成请求模板

参考：
- OpenAPI 3.0 Specification (https://swagger.io/specification/)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path
import logging
import re


logger = logging.getLogger(__name__)


@dataclass
class APIParameter:
    """API 参数"""
    name: str
    in_location: str  # path, query, header, cookie
    required: bool
    schema: Dict[str, Any]
    description: str = ""
    default: Any = None
    example: Any = None


@dataclass
class APIRequestBody:
    """请求体"""
    content_type: str
    schema: Dict[str, Any]
    required: bool = True
    description: str = ""


@dataclass
class APIResponse:
    """响应"""
    status_code: str
    description: str
    content_type: str = ""
    schema: Dict[str, Any] = field(default_factory=dict)


@dataclass
class APIEndpoint:
    """API 端点"""
    path: str
    method: str
    operation_id: str
    summary: str
    description: str
    parameters: List[APIParameter]
    request_body: Optional[APIRequestBody]
    responses: List[APIResponse]
    tags: List[str] = field(default_factory=list)
    security: List[Dict[str, Any]] = field(default_factory=list)
    deprecated: bool = False

    def get_tool_name(self) -> str:
        """生成工具名称"""
        if self.operation_id:
            # 转换为 snake_case
            name = re.sub(r'([A-Z]+)', r'_\1', self.operation_id).lower()
            return name.strip('_')

        # 从路径生成
        path_name = self.path.replace('/', '_').replace('{', '').replace('}', '')
        return f"{self.method}{path_name}"


@dataclass
class OpenAPISpec:
    """OpenAPI 规范"""
    title: str
    version: str
    description: str
    base_url: str
    endpoints: List[APIEndpoint]
    security_schemes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    raw_spec: Dict[str, Any] = field(default_factory=dict)


class OpenAPIParser:
    """
    OpenAPI 解析器

    解析 OpenAPI 3.0 规范文件。

    使用方式：
        parser = OpenAPIParser()
        spec = parser.parse("openapi.yaml")

        for endpoint in spec.endpoints:
            print(f"{endpoint.method.upper()} {endpoint.path}")
    """

    def __init__(self):
        """初始化解析器"""
        self._yaml = None

    def _load_yaml(self):
        """延迟加载 YAML 库"""
        if self._yaml is None:
            try:
                import yaml
                self._yaml = yaml
            except ImportError:
                raise ImportError("请安装 PyYAML: pip install pyyaml")
        return self._yaml

    def parse(self, spec_path: str) -> OpenAPISpec:
        """
        解析 OpenAPI 规范文件

        Args:
            spec_path: 规范文件路径（YAML 或 JSON）

        Returns:
            OpenAPISpec: 解析后的规范对象
        """
        path = Path(spec_path)
        if not path.exists():
            raise FileNotFoundError(f"OpenAPI 规范文件不存在: {spec_path}")

        content = path.read_text(encoding="utf-8")

        # 根据扩展名解析
        if path.suffix.lower() in {".yaml", ".yml"}:
            yaml = self._load_yaml()
            spec_data = yaml.safe_load(content)
        else:
            import json
            spec_data = json.loads(content)

        return self._parse_spec(spec_data)

    def parse_from_dict(self, spec_data: Dict[str, Any]) -> OpenAPISpec:
        """
        从字典解析 OpenAPI 规范

        Args:
            spec_data: 规范数据字典

        Returns:
            OpenAPISpec: 解析后的规范对象
        """
        return self._parse_spec(spec_data)

    def _parse_spec(self, data: Dict[str, Any]) -> OpenAPISpec:
        """解析规范数据"""
        # 基本信息
        info = data.get("info", {})
        title = info.get("title", "Unknown API")
        version = info.get("version", "1.0.0")
        description = info.get("description", "")

        # Base URL
        servers = data.get("servers", [])
        base_url = servers[0].get("url", "") if servers else ""

        # 安全方案
        security_schemes = {}
        components = data.get("components", {})
        if "securitySchemes" in components:
            security_schemes = components["securitySchemes"]

        # 解析端点
        endpoints = []
        paths = data.get("paths", {})
        for path, path_item in paths.items():
            for method in ["get", "post", "put", "patch", "delete"]:
                if method in path_item:
                    endpoint = self._parse_endpoint(path, method, path_item[method])
                    endpoints.append(endpoint)

        return OpenAPISpec(
            title=title,
            version=version,
            description=description,
            base_url=base_url,
            endpoints=endpoints,
            security_schemes=security_schemes,
            raw_spec=data,
        )

    def _parse_endpoint(
        self,
        path: str,
        method: str,
        operation: Dict[str, Any]
    ) -> APIEndpoint:
        """解析单个端点"""
        # 基本信息
        operation_id = operation.get("operationId", "")
        summary = operation.get("summary", "")
        description = operation.get("description", "")
        tags = operation.get("tags", [])
        security = operation.get("security", [])
        deprecated = operation.get("deprecated", False)

        # 参数
        parameters = []
        for param in operation.get("parameters", []):
            parameters.append(APIParameter(
                name=param.get("name", ""),
                in_location=param.get("in", "query"),
                required=param.get("required", False),
                schema=param.get("schema", {}),
                description=param.get("description", ""),
                default=param.get("schema", {}).get("default"),
                example=param.get("example"),
            ))

        # 请求体
        request_body = None
        if "requestBody" in operation:
            rb = operation["requestBody"]
            content = rb.get("content", {})
            if content:
                # 优先使用 application/json
                for ct in ["application/json", "application/x-www-form-urlencoded", "*/*"]:
                    if ct in content:
                        request_body = APIRequestBody(
                            content_type=ct,
                            schema=content[ct].get("schema", {}),
                            required=rb.get("required", True),
                            description=rb.get("description", ""),
                        )
                        break

        # 响应
        responses = []
        for status_code, response in operation.get("responses", {}).items():
            content = response.get("content", {})
            content_type = ""
            schema = {}
            if content:
                for ct in ["application/json", "*/*"]:
                    if ct in content:
                        content_type = ct
                        schema = content[ct].get("schema", {})
                        break

            responses.append(APIResponse(
                status_code=status_code,
                description=response.get("description", ""),
                content_type=content_type,
                schema=schema,
            ))

        return APIEndpoint(
            path=path,
            method=method,
            operation_id=operation_id,
            summary=summary,
            description=description,
            parameters=parameters,
            request_body=request_body,
            responses=responses,
            tags=tags,
            security=security,
            deprecated=deprecated,
        )

    def generate_tool_manifest(self, spec: OpenAPISpec) -> List[Dict[str, Any]]:
        """
        生成工具清单（用于 MCP 或 Agent）

        Args:
            spec: OpenAPI 规范对象

        Returns:
            List[Dict]: 工具清单
        """
        tools = []
        for endpoint in spec.endpoints:
            if endpoint.deprecated:
                continue

            # 构建输入 schema
            input_schema = {
                "type": "object",
                "properties": {},
                "required": [],
            }

            # 添加参数
            for param in endpoint.parameters:
                prop = param.schema.copy()
                if param.description:
                    prop["description"] = param.description
                if param.example:
                    prop["example"] = param.example
                input_schema["properties"][param.name] = prop
                if param.required:
                    input_schema["required"].append(param.name)

            # 添加请求体
            if endpoint.request_body:
                body_schema = endpoint.request_body.schema.copy()
                if "$ref" in body_schema:
                    # 解析 $ref（简化处理）
                    ref_path = body_schema["$ref"].split("/")[-1]
                    input_schema["properties"]["body"] = {
                        "type": "object",
                        "description": f"请求体 ({ref_path})",
                    }
                else:
                    input_schema["properties"]["body"] = body_schema
                if endpoint.request_body.required:
                    input_schema["required"].append("body")

            tool = {
                "name": endpoint.get_tool_name(),
                "description": endpoint.summary or endpoint.description or f"{endpoint.method.upper()} {endpoint.path}",
                "inputSchema": input_schema,
                "metadata": {
                    "path": endpoint.path,
                    "method": endpoint.method,
                    "operation_id": endpoint.operation_id,
                }
            }
            tools.append(tool)

        return tools


def parse_openapi(spec_path: str) -> OpenAPISpec:
    """
    快捷函数：解析 OpenAPI 规范

    Args:
        spec_path: 规范文件路径

    Returns:
        OpenAPISpec: 解析后的规范对象
    """
    parser = OpenAPIParser()
    return parser.parse(spec_path)
