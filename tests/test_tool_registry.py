"""
ToolRegistry 单元测试

测试工具注册表的所有核心功能：
- 工具注册（各种类型）
- 工具查询和检索
- OpenAPI Schema 生成
- 工具执行
- 动态添加/移除
"""

import asyncio
import pytest
from typing import Dict, Any

import sys
from pathlib import Path

# 添加 src 到路径
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# 直接导入模块
from src.agent.tool import (
    Tool, ToolType, ToolParameter, ToolResult, create_tool_from_function
)
from src.agent.tool_registry import ToolRegistry, get_global_registry, reset_global_registry


# ============================================================================
# 测试工具定义
# ============================================================================

class TestTool:
    """测试 Tool 类"""

    def test_tool_creation(self):
        """测试工具创建"""
        tool = Tool(
            name="test_tool",
            type=ToolType.CUSTOM,
            description="Test tool",
            parameters=[
                ToolParameter(name="param1", type="string", required=True)
            ]
        )

        assert tool.name == "test_tool"
        assert tool.type == ToolType.CUSTOM
        assert tool.description == "Test tool"
        assert len(tool.parameters) == 1
        assert tool.enabled is True

    def test_tool_to_openapi_schema(self):
        """测试 OpenAPI Schema 生成"""
        tool = Tool(
            name="test_tool",
            type=ToolType.CUSTOM,
            description="Test tool",
            parameters=[
                ToolParameter(
                    name="text",
                    type="string",
                    description="Input text",
                    required=True
                ),
                ToolParameter(
                    name="count",
                    type="number",
                    description="Repeat count",
                    required=False,
                    default=1
                )
            ]
        )

        schema = tool.to_openapi_schema()

        assert schema["name"] == "test_tool"
        assert schema["description"] == "Test tool"
        assert "inputSchema" in schema
        assert schema["inputSchema"]["type"] == "object"
        assert "properties" in schema["inputSchema"]
        assert "text" in schema["inputSchema"]["properties"]
        assert "count" in schema["inputSchema"]["properties"]
        assert schema["inputSchema"]["required"] == ["text"]
        assert schema["x-tool-type"] == "custom"

    def test_tool_from_skill(self):
        """测试从 Skill 创建工具"""
        tool = Tool.from_skill(
            skill_name="my_skill",
            description="My skill description"
        )

        assert tool.name == "skill.my_skill"
        assert tool.type == ToolType.SKILL
        assert tool.description == "My skill description"
        assert len(tool.parameters) == 2  # user_input, context

    def test_tool_from_mcp_tool(self):
        """测试从 MCP 工具创建"""
        def handler(**kwargs):
            return ToolResult(success=True, data="ok")

        tool = Tool.from_mcp_tool(
            server_name="filesystem",
            tool_name="read_file",
            description="Read a file",
            parameters=[
                ToolParameter(name="path", type="string", required=True)
            ],
            handler=handler
        )

        assert tool.name == "mcp.filesystem.read_file"
        assert tool.type == ToolType.MCP
        assert tool.metadata["server_name"] == "filesystem"
        assert tool.metadata["tool_name"] == "read_file"

    def test_tool_from_subagent(self):
        """测试从 SubAgent 创建工具"""
        def handler(**kwargs):
            return ToolResult(success=True, data="ok")

        tool = Tool.from_subagent(
            agent_id="code_analyzer",
            description="Analyze code",
            handler=handler
        )

        assert tool.name == "subagent.code_analyzer"
        assert tool.type == ToolType.SUBAGENT

    def test_tool_execute_sync(self):
        """测试同步工具执行"""
        def my_handler(text: str) -> str:
            return f"Processed: {text}"

        tool = Tool.from_function(
            name="test_tool",
            func=my_handler,
            description="Test"
        )

        result = asyncio.run(tool.execute(text="hello"))

        assert result.success is True
        assert result.data == "Processed: hello"

    def test_tool_execute_async(self):
        """测试异步工具执行"""
        async def my_handler(text: str) -> str:
            await asyncio.sleep(0.01)
            return f"Async: {text}"

        tool = Tool.from_function(
            name="test_tool",
            func=my_handler,
            description="Test"
        )

        result = asyncio.run(tool.execute(text="hello"))

        assert result.success is True
        assert result.data == "Async: hello"


class TestToolParameter:
    """测试 ToolParameter 类"""

    def test_parameter_to_openapi(self):
        """测试参数 OpenAPI 转换"""
        param = ToolParameter(
            name="test_param",
            type="string",
            description="Test parameter",
            required=True,
            default="default_value"
        )

        schema = param.to_openapi()

        assert schema["type"] == "string"
        assert schema["description"] == "Test parameter"
        assert schema["default"] == "default_value"

    def test_parameter_with_enum(self):
        """测试带枚举值的参数"""
        param = ToolParameter(
            name="color",
            type="string",
            enum=["red", "green", "blue"]
        )

        schema = param.to_openapi()

        assert "enum" in schema
        assert schema["enum"] == ["red", "green", "blue"]


class TestCreateToolFromFunction:
    """测试从函数创建工具"""

    def test_simple_function(self):
        """测试简单函数"""
        def greet(name: str) -> str:
            return f"Hello, {name}!"

        tool = create_tool_from_function(greet)

        assert tool.name == "greet"
        assert tool.type == ToolType.CUSTOM
        assert len(tool.parameters) == 1
        assert tool.parameters[0].name == "name"
        assert tool.parameters[0].type == "string"

    def test_function_with_multiple_params(self):
        """测试多参数函数"""
        def process(text: str, count: int, verbose: bool = False) -> str:
            return f"{text} * {count}"

        tool = create_tool_from_function(process)

        assert len(tool.parameters) == 3
        assert tool.parameters[0].name == "text"
        assert tool.parameters[1].name == "count"
        assert tool.parameters[2].name == "verbose"
        assert tool.parameters[2].required is False  # 有默认值

    def test_function_with_docstring(self):
        """测试带文档字符串的函数"""
        def my_function(x: int) -> int:
            """This is a test function."""
            return x * 2

        tool = create_tool_from_function(my_function)

        assert "test function" in tool.description


# ============================================================================
# 测试工具注册表
# ============================================================================

class TestToolRegistry:
    """测试 ToolRegistry 类"""

    def test_register_decorator(self):
        """测试装饰器注册"""
        registry = ToolRegistry()

        @registry.register("test_tool", description="Test tool")
        def my_function(text: str) -> str:
            return f"Processed: {text}"

        # 验证注册
        assert "test_tool" in registry
        tool = registry.get("test_tool")
        assert tool is not None
        assert tool.name == "test_tool"
        assert tool.description == "Test tool"

    def test_register_tool(self):
        """测试直接注册工具"""
        registry = ToolRegistry()

        tool = Tool(
            name="test_tool",
            type=ToolType.CUSTOM,
            description="Test"
        )

        registry.register_tool(tool)

        assert "test_tool" in registry
        assert registry.get("test_tool") == tool

    def test_register_skill(self):
        """测试注册 Skill"""
        registry = ToolRegistry()

        tool = registry.register_skill(
            skill_name="my_skill",
            description="My skill"
        )

        assert "skill.my_skill" in registry
        assert tool.type == ToolType.SKILL
        assert tool.name == "skill.my_skill"

    def test_register_mcp_tool(self):
        """测试注册 MCP 工具"""
        registry = ToolRegistry()

        def handler(**kwargs):
            return ToolResult(success=True, data="ok")

        tool = registry.register_mcp_tool(
            server_name="filesystem",
            tool_name="read_file",
            description="Read file",
            handler=handler
        )

        assert "mcp.filesystem.read_file" in registry
        assert tool.type == ToolType.MCP

    def test_register_subagent(self):
        """测试注册 SubAgent"""
        registry = ToolRegistry()

        def handler(**kwargs):
            return ToolResult(success=True, data="ok")

        tool = registry.register_subagent(
            agent_id="code_analyzer",
            description="Analyze code",
            handler=handler
        )

        assert "subagent.code_analyzer" in registry
        assert tool.type == ToolType.SUBAGENT

    def test_unregister(self):
        """测试注销工具"""
        registry = ToolRegistry()

        @registry.register("test_tool")
        def my_function():
            pass

        assert "test_tool" in registry
        assert registry.unregister("test_tool") is True
        assert "test_tool" not in registry
        assert registry.unregister("test_tool") is False  # 不存在

    def test_get(self):
        """测试获取工具"""
        registry = ToolRegistry()

        @registry.register("test_tool")
        def my_function():
            pass

        tool = registry.get("test_tool")
        assert tool is not None

        tool = registry.get("nonexistent")
        assert tool is None

    def test_list_tools(self):
        """测试列出工具"""
        registry = ToolRegistry()

        @registry.register("tool1")
        def func1():
            pass

        @registry.register("tool2")
        def func2():
            pass

        registry.register_skill("skill1", "Skill 1")
        registry.register_subagent("agent1", "Agent 1", lambda **kwargs: ToolResult(success=True))

        # 列出所有工具
        all_tools = registry.list_tools()
        assert len(all_tools) == 4

        # 按类型过滤
        custom_tools = registry.list_tools(type=ToolType.CUSTOM)
        assert len(custom_tools) == 2

        skill_tools = registry.list_tools(type=ToolType.SKILL)
        assert len(skill_tools) == 1

    def test_list_tool_names(self):
        """测试列出工具名称"""
        registry = ToolRegistry()

        @registry.register("tool1")
        def func1():
            pass

        @registry.register("tool2")
        def func2():
            pass

        names = registry.list_tool_names()
        assert "tool1" in names
        assert "tool2" in names

    def test_enable_disable(self):
        """测试启用/禁用工具"""
        registry = ToolRegistry()

        @registry.register("test_tool")
        def my_function():
            pass

        # 默认启用
        assert registry.get("test_tool").enabled is True

        # 禁用
        assert registry.disable("test_tool") is True
        assert registry.get("test_tool").enabled is False

        # 启用
        assert registry.enable("test_tool") is True
        assert registry.get("test_tool").enabled is True

    def test_execute(self):
        """测试执行工具"""
        registry = ToolRegistry()

        @registry.register("test_tool")
        def my_function(text: str) -> str:
            return f"Processed: {text}"

        result = asyncio.run(registry.execute("test_tool", text="hello"))

        assert result.success is True
        assert result.data == "Processed: hello"

    def test_execute_nonexistent_tool(self):
        """测试执行不存在的工具"""
        registry = ToolRegistry()

        result = asyncio.run(registry.execute("nonexistent"))

        assert result.success is False
        assert "不存在" in result.error

    def test_to_openapi_schema_flat(self):
        """测试生成扁平化 OpenAPI Schema"""
        registry = ToolRegistry()

        @registry.register("tool1", description="Tool 1")
        def func1(text: str) -> str:
            return text

        registry.register_skill("skill1", "Skill 1")

        schema = registry.to_openapi_schema(group_by_type=False)

        assert "tools" in schema
        assert isinstance(schema["tools"], list)
        assert len(schema["tools"]) == 2

        assert "stats" in schema
        assert schema["stats"]["total"] == 2

    def test_to_openapi_schema_grouped(self):
        """测试生成分组 OpenAPI Schema"""
        registry = ToolRegistry()

        @registry.register("tool1", description="Tool 1")
        def func1(text: str) -> str:
            return text

        registry.register_skill("skill1", "Skill 1")

        schema = registry.to_openapi_schema(group_by_type=True)

        assert "tools" in schema
        assert isinstance(schema["tools"], dict)
        assert "custom" in schema["tools"]
        assert "skill" in schema["tools"]

    def test_count(self):
        """测试统计工具数量"""
        registry = ToolRegistry()

        @registry.register("tool1")
        def func1():
            pass

        @registry.register("tool2")
        def func2():
            pass

        registry.register_skill("skill1", "Skill 1")

        assert registry.count() == 3
        assert registry.count(type=ToolType.CUSTOM) == 2
        assert registry.count(type=ToolType.SKILL) == 1

    def test_clear(self):
        """测试清空注册表"""
        registry = ToolRegistry()

        @registry.register("tool1")
        def func1():
            pass

        assert len(registry) == 1

        registry.clear()

        assert len(registry) == 0

    def test_len_and_contains(self):
        """测试 __len__ 和 __contains__"""
        registry = ToolRegistry()

        @registry.register("tool1")
        def func1():
            pass

        assert len(registry) == 1
        assert "tool1" in registry
        assert "tool2" not in registry

    def test_iteration(self):
        """测试迭代"""
        registry = ToolRegistry()

        @registry.register("tool1")
        def func1():
            pass

        @registry.register("tool2")
        def func2():
            pass

        names = [tool.name for tool in registry]
        assert "tool1" in names
        assert "tool2" in names


class TestGlobalRegistry:
    """测试全局注册表"""

    def test_get_global_registry(self):
        """测试获取全局注册表"""
        reset_global_registry()

        registry1 = get_global_registry()
        registry2 = get_global_registry()

        assert registry1 is registry2  # 同一实例

    def test_global_registry_register(self):
        """测试全局注册表注册"""
        reset_global_registry()

        registry = get_global_registry()

        @registry.register("global_tool")
        def my_function():
            pass

        assert "global_tool" in registry


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v", "--tb=short"])
