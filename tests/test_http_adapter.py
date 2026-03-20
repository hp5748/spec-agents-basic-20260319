"""
HTTP Adapter 单元测试
"""

import pytest
import respx
from src.adapters.http.client import HTTPAdapter, HTTPEndpoint, create_http_adapter
from src.adapters.http.config import HTTPConfigLoader
from src.adapters.core.types import ToolRequest


class TestHTTPEndpoint:
    """HTTPEndpoint 测试"""

    def test_create_endpoint(self):
        """测试创建端点"""
        endpoint = HTTPEndpoint(
            name="get_user",
            method="GET",
            path="/users/{id}",
            description="获取用户信息",
        )

        assert endpoint.name == "get_user"
        assert endpoint.method == "GET"
        assert endpoint.path == "/users/{id}"
        assert "id" in endpoint.path_params

    def test_get_url(self):
        """测试 URL 构建"""
        endpoint = HTTPEndpoint(
            name="test",
            method="GET",
            path="/users/{id}",
        )

        url = endpoint.get_url("https://api.example.com", {"id": "123"})
        assert url == "https://api.example.com/users/123"


class TestHTTPAdapter:
    """HTTPAdapter 测试"""

    @pytest.fixture
    async def adapter(self):
        """创建适配器实例"""
        adapter = HTTPAdapter(base_url="https://api.example.com")
        await adapter.initialize()
        yield adapter
        await adapter.shutdown()

    @pytest.mark.asyncio
    async def test_initialize_shutdown(self, adapter):
        """测试初始化和关闭"""
        assert adapter._initialized is True
        assert adapter._client is not None

    @pytest.mark.asyncio
    async def test_register_endpoint(self, adapter):
        """测试注册端点"""
        endpoint = HTTPEndpoint(
            name="get_user",
            method="GET",
            path="/users/{id}",
        )

        adapter.register_endpoint(endpoint)

        assert "get_user" in adapter.list_endpoints()

    @pytest.mark.asyncio
    @respx.mock
    async def test_execute_get_request(self, adapter):
        """测试执行 GET 请求"""
        # 注册端点
        endpoint = HTTPEndpoint(
            name="get_user",
            method="GET",
            path="/users/{id}",
        )
        adapter.register_endpoint(endpoint)

        # Mock 响应
        request = respx.get("https://api.example.com/users/123").mock(
            return_value=respx.Response(200, json={"id": "123", "name": "Test User"})
        )

        # 执行请求
        response = await adapter.execute(
            ToolRequest(tool_name="get_user", parameters={"id": "123"})
        )

        assert response.success is True
        assert response.data["id"] == "123"
        assert response.metadata["status_code"] == 200

    @pytest.mark.asyncio
    @respx.mock
    async def test_execute_post_request(self, adapter):
        """测试执行 POST 请求"""
        endpoint = HTTPEndpoint(
            name="create_user",
            method="POST",
            path="/users",
        )
        adapter.register_endpoint(endpoint)

        request = respx.post("https://api.example.com/users").mock(
            return_value=respx.Response(201, json={"id": "456", "name": "New User"})
        )

        response = await adapter.execute(
            ToolRequest(
                tool_name="create_user", parameters={"name": "New User", "email": "test@example.com"}
            )
        )

        assert response.success is True
        assert response.data["id"] == "456"

    @pytest.mark.asyncio
    async def test_execute_nonexistent_endpoint(self, adapter):
        """测试执行不存在的端点"""
        response = await adapter.execute(
            ToolRequest(tool_name="nonexistent", parameters={})
        )

        assert response.success is False
        assert "不存在" in response.error

    @pytest.mark.asyncio
    @respx.mock
    async def test_http_error_handling(self, adapter):
        """测试 HTTP 错误处理"""
        endpoint = HTTPEndpoint(name="error_test", method="GET", path="/error")
        adapter.register_endpoint(endpoint)

        respx.get("https://api.example.com/error").mock(
            return_value=respx.Response(404, text="Not Found")
        )

        response = await adapter.execute(
            ToolRequest(tool_name="error_test", parameters={})
        )

        assert response.success is False
        assert "404" in response.error

    @pytest.mark.asyncio
    async def test_health_check(self, adapter):
        """测试健康检查"""
        status = await adapter.health_check()

        assert status.healthy is True
        assert status.base_url == "https://api.example.com"


class TestConfigLoader:
    """配置加载器测试"""

    def test_parse_env(self):
        """测试环境变量解析"""
        import os

        os.environ["TEST_VAR"] = "test_value"

        loader = HTTPConfigLoader()
        result = loader._parse_env("https://api.${TEST_VAR}.com")

        assert result == "https://api.test_value.com"

        # 清理
        del os.environ["TEST_VAR"]


class TestCreateAdapter:
    """创建适配器测试"""

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_http_adapter(self):
        """测试便捷创建函数"""
        endpoints = [
            {"name": "test", "method": "GET", "path": "/test"}
        ]

        respx.get("https://api.example.com/test").mock(
            return_value=respx.Response(200, json={"ok": True})
        )

        adapter = await create_http_adapter(
            name="test_adapter",
            base_url="https://api.example.com",
            endpoints=endpoints,
        )

        assert adapter._initialized is True
        assert "test" in adapter.list_endpoints()

        await adapter.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
