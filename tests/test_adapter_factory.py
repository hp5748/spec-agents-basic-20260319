"""
Adapter Factory 单元测试

测试适配器工厂的核心功能。
"""

import asyncio
import pytest
import pytest_asyncio

from src.adapters.core import (
    AdapterFactory,
    AdapterType,
    AdapterConfig,
    ToolRequest,
    ToolResponse,
    MockAdapter,
    BaseAdapter
)


class TestAdapterConfig:
    """测试适配器配置"""

    def test_config_creation(self):
        """测试配置创建"""
        config = AdapterConfig(
            type=AdapterType.CUSTOM,
            name="test_adapter",
            enabled=True,
            timeout=30
        )

        assert config.type == AdapterType.CUSTOM
        assert config.name == "test_adapter"
        assert config.enabled is True
        assert config.timeout == 30

    def test_config_to_dict(self):
        """测试配置转字典"""
        config = AdapterConfig(
            type=AdapterType.MCP,
            name="mcp_adapter",
            metadata={"key": "value"}
        )

        config_dict = config.to_dict()

        assert config_dict["type"] == "mcp"
        assert config_dict["name"] == "mcp_adapter"
        assert config_dict["metadata"] == {"key": "value"}


class TestToolRequestResponse:
    """测试工具请求和响应"""

    def test_request_creation(self):
        """测试请求创建"""
        request = ToolRequest(
            tool_name="echo",
            parameters={"message": "hello"},
            session_id="test_session"
        )

        assert request.tool_name == "echo"
        assert request.parameters["message"] == "hello"
        assert request.session_id == "test_session"

    def test_response_from_success(self):
        """测试成功响应"""
        response = ToolResponse.from_success(
            data="result data",
            tool_name="test_tool"
        )

        assert response.success is True
        assert response.data == "result data"
        assert response.tool_name == "test_tool"
        assert response.error is None

    def test_response_from_error(self):
        """测试错误响应"""
        response = ToolResponse.from_error(
            error="Something went wrong",
            tool_name="test_tool"
        )

        assert response.success is False
        assert response.error == "Something went wrong"
        assert response.tool_name == "test_tool"

    def test_response_to_dict(self):
        """测试响应转字典"""
        response = ToolResponse(
            success=True,
            data="test",
            adapter_type="custom",
            tool_name="test_tool"
        )

        response_dict = response.to_dict()

        assert response_dict["success"] is True
        assert response_dict["data"] == "test"
        assert response_dict["adapter_type"] == "custom"


class MockCustomAdapter(BaseAdapter):
    """自定义 Mock 适配器（用于测试）"""

    def __init__(self, config: AdapterConfig):
        super().__init__(config)
        self.initialized = False
        self.shutdown_called = False

    async def initialize(self):
        self.initialized = True

    async def execute(self, request: ToolRequest) -> ToolResponse:
        if request.tool_name == "test_success":
            return ToolResponse.from_success(
                data="test result",
                tool_name=request.tool_name
            )
        elif request.tool_name == "test_error":
            return ToolResponse.from_error(
                error="test error",
                tool_name=request.tool_name
            )
        else:
            return ToolResponse.from_error(
                error=f"Unknown tool: {request.tool_name}",
                tool_name=request.tool_name
            )

    async def shutdown(self):
        self.shutdown_called = True

    def get_capabilities(self):
        from src.adapters.core import AdapterCapabilities
        return AdapterCapabilities(
            tools=["test_success", "test_error"]
        )


class TestAdapterFactory:
    """测试适配器工厂"""

    @pytest.fixture
    def factory(self):
        """创建工厂实例"""
        return AdapterFactory()

    @pytest_asyncio.fixture
    async def custom_adapter(self, factory):
        """创建自定义适配器"""
        factory.register_adapter_class(
            AdapterType.CUSTOM,
            MockCustomAdapter
        )

        config = AdapterConfig(
            type=AdapterType.CUSTOM,
            name="custom_test_adapter"
        )

        adapter = await factory.create_adapter(config)
        yield adapter

        await factory.remove_adapter("custom_test_adapter")

    @pytest.mark.asyncio
    async def test_register_adapter_class(self, factory):
        """测试注册适配器类"""
        factory.register_adapter_class(
            AdapterType.CUSTOM,
            MockCustomAdapter
        )

        assert AdapterType.CUSTOM in factory._adapter_classes

    @pytest.mark.asyncio
    async def test_register_invalid_adapter_class(self, factory):
        """测试注册无效的适配器类"""
        with pytest.raises(ValueError):
            factory.register_adapter_class(
                AdapterType.CUSTOM,
                str  # str 不继承 BaseAdapter
            )

    @pytest.mark.asyncio
    async def test_create_adapter(self, factory):
        """测试创建适配器"""
        factory.register_adapter_class(
            AdapterType.CUSTOM,
            MockCustomAdapter
        )

        config = AdapterConfig(
            type=AdapterType.CUSTOM,
            name="test_adapter"
        )

        adapter = await factory.create_adapter(config)

        assert adapter is not None
        assert adapter.config.name == "test_adapter"
        assert adapter.initialized is True

    @pytest.mark.asyncio
    async def test_create_unsupported_adapter_type(self, factory):
        """测试创建不支持的适配器类型"""
        config = AdapterConfig(
            type=AdapterType.SKILL,  # 未注册的类型
            name="test_adapter"
        )

        with pytest.raises(ValueError):
            await factory.create_adapter(config)

    @pytest.mark.asyncio
    async def test_route_to_custom_adapter(self, custom_adapter, factory):
        """测试路由到自定义适配器"""
        response = await factory.route(
            tool_name="test_success",
            parameters={},
            session_id="test_session"
        )

        assert response.success is True
        assert response.data == "test result"

    @pytest.mark.asyncio
    async def test_route_error(self, custom_adapter, factory):
        """测试路由错误"""
        response = await factory.route(
            tool_name="test_error",
            parameters={}
        )

        assert response.success is False
        assert response.error == "test error"

    @pytest.mark.asyncio
    async def test_route_unknown_tool(self, factory):
        """测试路由未知工具"""
        response = await factory.route(
            tool_name="unknown_tool",
            parameters={}
        )

        assert response.success is False
        assert "未注册" in response.error

    @pytest.mark.asyncio
    async def test_list_adapters(self, custom_adapter, factory):
        """测试列出适配器"""
        adapters = factory.list_adapters()

        assert len(adapters) == 1
        assert adapters[0].config.name == "custom_test_adapter"

    @pytest.mark.asyncio
    async def test_list_adapter_names(self, custom_adapter, factory):
        """测试列出适配器名称"""
        names = factory.list_adapter_names()

        assert len(names) == 1
        assert names[0] == "custom_test_adapter"

    @pytest.mark.asyncio
    async def test_list_tools(self, custom_adapter, factory):
        """测试列出工具"""
        tools = factory.list_tools()

        assert "test_success" in tools
        assert "test_error" in tools

    @pytest.mark.asyncio
    async def test_list_tools_by_adapter(self, custom_adapter, factory):
        """测试按适配器列出工具"""
        tools = factory.list_tools(adapter_name="custom_test_adapter")

        assert "test_success" in tools
        assert "test_error" in tools

    @pytest.mark.asyncio
    async def test_remove_adapter(self, custom_adapter, factory):
        """测试移除适配器"""
        success = await factory.remove_adapter("custom_test_adapter")

        assert success is True
        assert "custom_test_adapter" not in factory._adapters

    @pytest.mark.asyncio
    async def test_health_check_all(self, custom_adapter, factory):
        """测试健康检查（全部）"""
        results = await factory.health_check()

        assert "custom_test_adapter" in results
        assert results["custom_test_adapter"]["healthy"] is True

    @pytest.mark.asyncio
    async def test_health_check_single(self, custom_adapter, factory):
        """测试健康检查（单个）"""
        result = await factory.health_check(adapter_name="custom_test_adapter")

        assert result["adapter_name"] == "custom_test_adapter"
        assert result["status"]["healthy"] is True

    @pytest.mark.asyncio
    async def test_get_stats(self, custom_adapter, factory):
        """测试获取统计信息"""
        stats = factory.get_stats()

        assert stats["total_adapters"] == 1
        assert stats["total_tools"] == 2
        assert "custom" in stats["by_type"]

    @pytest.mark.asyncio
    async def test_shutdown_all(self, factory):
        """测试关闭所有适配器"""
        factory.register_adapter_class(
            AdapterType.CUSTOM,
            MockCustomAdapter
        )

        config = AdapterConfig(
            type=AdapterType.CUSTOM,
            name="test_adapter"
        )

        adapter = await factory.create_adapter(config)

        await factory.shutdown_all()

        assert len(factory._adapters) == 0
        assert len(factory._tool_mapping) == 0
        assert adapter.shutdown_called is True


class TestMockAdapter:
    """测试 Mock 适配器"""

    @pytest_asyncio.fixture
    async def mock_adapter(self):
        """创建 Mock 适配器"""
        config = AdapterConfig(
            type=AdapterType.CUSTOM,
            name="mock_adapter"
        )

        adapter = MockAdapter(config)
        await adapter.initialize()
        yield adapter
        await adapter.shutdown()

    @pytest.mark.asyncio
    async def test_echo_tool(self, mock_adapter):
        """测试 echo 工具"""
        request = ToolRequest(
            tool_name="echo",
            parameters={"message": "hello"}
        )

        response = await mock_adapter.execute(request)

        assert response.success is True
        assert response.data == "Echo: hello"

    @pytest.mark.asyncio
    async def test_add_tool(self, mock_adapter):
        """测试 add 工具"""
        request = ToolRequest(
            tool_name="add",
            parameters={"a": 3, "b": 5}
        )

        response = await mock_adapter.execute(request)

        assert response.success is True
        assert response.data["result"] == 8

    @pytest.mark.asyncio
    async def test_fail_tool(self, mock_adapter):
        """测试 fail 工具"""
        request = ToolRequest(
            tool_name="fail",
            parameters={}
        )

        response = await mock_adapter.execute(request)

        assert response.success is False
        assert "always fails" in response.error

    @pytest.mark.asyncio
    async def test_unknown_tool(self, mock_adapter):
        """测试未知工具"""
        request = ToolRequest(
            tool_name="unknown",
            parameters={}
        )

        response = await mock_adapter.execute(request)

        assert response.success is False
        assert "not found" in response.error


class TestGlobalFactory:
    """测试全局工厂"""

    def test_get_global_factory(self):
        """测试获取全局工厂"""
        from src.adapters.core import reset_global_factory, get_global_factory

        reset_global_factory()

        factory1 = get_global_factory()
        factory2 = get_global_factory()

        # 应该返回同一个实例
        assert factory1 is factory2

    def test_reset_global_factory(self):
        """测试重置全局工厂"""
        from src.adapters.core import reset_global_factory, get_global_factory

        factory1 = get_global_factory()
        reset_global_factory()
        factory2 = get_global_factory()

        # 重置后应该是不同的实例
        assert factory1 is not factory2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
