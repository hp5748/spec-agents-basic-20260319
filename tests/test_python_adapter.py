"""
Python Adapter 单元测试
"""

import pytest
import asyncio
from src.adapters.python.executor import (
    PythonAdapter,
    PythonFunction,
    register_python_function,
    get_python_adapter,
)
from src.adapters.python.sandbox import PythonSandbox, SandboxError
from src.adapters.python.loader import SkillLoader, SkillMetadata


class TestPythonFunction:
    """PythonFunction 测试"""

    def test_create_function(self):
        """测试创建函数包装器"""
        def add(a: int, b: int) -> int:
            return a + b

        func = PythonFunction("add", add, "加法运算")

        assert func.name == "add"
        assert func.description == "加法运算"
        assert not func.is_async
        assert "a" in func.parameters["properties"]
        assert "b" in func.parameters["properties"]

    def test_async_function_detection(self):
        """测试异步函数检测"""
        async def async_func():
            return "async"

        func = PythonFunction("async_func", async_func)

        assert func.is_async

    def test_type_conversion(self):
        """测试类型转换"""
        def func(
            s: str,
            i: int,
            f: float,
            b: bool,
            l: list,
            d: dict,
        ) -> str:
            return "ok"

        pyfunc = PythonFunction("test", func)
        props = pyfunc.parameters["properties"]

        assert props["s"]["type"] == "string"
        assert props["i"]["type"] == "integer"
        assert props["f"]["type"] == "number"
        assert props["b"]["type"] == "boolean"
        assert props["l"]["type"] == "array"
        assert props["d"]["type"] == "object"


class TestPythonAdapter:
    """PythonAdapter 测试"""

    @pytest.fixture
    async def adapter(self):
        """创建适配器实例"""
        adapter = PythonAdapter()
        await adapter.initialize()
        yield adapter
        await adapter.shutdown()

    @pytest.mark.asyncio
    async def test_initialize_shutdown(self, adapter):
        """测试初始化和关闭"""
        assert adapter._initialized is True

    @pytest.mark.asyncio
    async def test_register_function(self, adapter):
        """测试注册函数"""
        def test_func(x: int) -> int:
            return x * 2

        adapter.register_function("double", test_func, "双倍运算")

        assert "double" in adapter.list_functions()
        assert adapter.get_function("double") is not None

    @pytest.mark.asyncio
    async def test_execute_sync_function(self, adapter):
        """测试执行同步函数"""
        def add(a: int, b: int) -> int:
            return a + b

        adapter.register_function("add", add, "加法运算")

        from src.adapters.core.types import ToolRequest

        response = await adapter.execute(
            ToolRequest(tool_name="add", parameters={"a": 10, "b": 20})
        )

        assert response.success is True
        assert response.data == 30

    @pytest.mark.asyncio
    async def test_execute_async_function(self, adapter):
        """测试执行异步函数"""
        async def async_greet(name: str) -> str:
            await asyncio.sleep(0.01)
            return f"Hello, {name}!"

        adapter.register_function("greet", async_greet, "异步问候")

        from src.adapters.core.types import ToolRequest

        response = await adapter.execute(
            ToolRequest(tool_name="greet", parameters={"name": "World"})
        )

        assert response.success is True
        assert response.data == "Hello, World!"

    @pytest.mark.asyncio
    async def test_execute_nonexistent_function(self, adapter):
        """测试执行不存在的函数"""
        from src.adapters.core.types import ToolRequest

        response = await adapter.execute(
            ToolRequest(tool_name="nonexistent", parameters={})
        )

        assert response.success is False
        assert "不存在" in response.error

    @pytest.mark.asyncio
    async def test_function_stats(self, adapter):
        """测试函数执行统计"""
        def test_func():
            return 1

        adapter.register_function("test", test_func)

        from src.adapters.core.types import ToolRequest

        await adapter.execute(ToolRequest(tool_name="test", parameters={}))
        await adapter.execute(ToolRequest(tool_name="test", parameters={}))

        stats = adapter._execution_stats["test"]
        assert stats["calls"] == 2
        assert stats["errors"] == 0

    @pytest.mark.asyncio
    async def test_health_check(self, adapter):
        """测试健康检查"""
        status = await adapter.health_check()

        assert status.healthy is True
        assert status.function_count == 0


class TestSandbox:
    """沙箱测试"""

    def test_safe_code_detection(self):
        """测试安全代码检测"""
        sandbox = PythonSandbox()

        assert sandbox.is_safe_code("x = 1 + 1") is True
        assert sandbox.is_safe_code("import json") is True
        assert sandbox.is_safe_code("import os") is False
        assert sandbox.is_safe_code("__import__('os')") is False

    @pytest.mark.asyncio
    async def test_execute_safe_code(self):
        """测试执行安全代码"""
        sandbox = PythonSandbox()

        result = await sandbox.execute_code("x = 1 + 1\n_result = x")
        assert result == 2

    @pytest.mark.asyncio
    async def test_blocked_import(self):
        """测试阻止导入"""
        sandbox = PythonSandbox()

        with pytest.raises(SandboxError):
            await sandbox.execute_code("import os")


class TestSkillLoader:
    """Skills 加载器测试"""

    def test_metadata_creation(self):
        """测试元数据创建"""
        metadata = SkillMetadata(
            name="test",
            description="测试技能",
            version="1.0.0",
        )

        assert metadata.name == "test"
        assert metadata.description == "测试技能"
        assert metadata.version == "1.0.0"


class TestGlobalAdapter:
    """全局适配器测试"""

    def test_get_global_adapter(self):
        """测试获取全局适配器"""
        adapter1 = get_python_adapter()
        adapter2 = get_python_adapter()

        assert adapter1 is adapter2

    def test_register_decorator(self):
        """测试注册装饰器"""
        adapter = get_python_adapter()

        @register_python_function("decorated_test", description="装饰器测试")
        def test_func(x: int) -> int:
            return x * 2

        assert "decorated_test" in adapter.list_functions()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
