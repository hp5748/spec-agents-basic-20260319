"""
ToolRegistry 使用示例

展示如何使用工具注册表统一管理所有类型的工具。
"""

import asyncio
import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent.tool import Tool, ToolType, ToolParameter
from agent.tool_registry import ToolRegistry


# ============================================================================
# 示例 1: 注册自定义工具
# ============================================================================

def example_custom_tool():
    """示例 1: 使用装饰器注册自定义工具"""
    registry = ToolRegistry()

    @registry.register("greet", description="向用户打招呼")
    def greet(name: str, title: str = "先生/女士") -> str:
        """
        向用户打招呼

        Args:
            name: 姓名
            title: 称呼

        Returns:
            打招呼的内容
        """
        return f"你好，{title} {name}！"

    # 执行工具
    result = asyncio.run(registry.execute("greet", name="张三", title="李先生"))
    print(f"结果: {result.data}")
    # 输出: 结果: 你好，李先生 张三！


# ============================================================================
# 示例 2: 注册 Skill 工具
# ============================================================================

def example_skill_tool():
    """示例 2: 注册 Skill 工具"""
    registry = ToolRegistry()

    # 模拟 Skill 执行函数
    async def execute_sqlite_query(user_input: str, context: dict = None) -> dict:
        return {
            "success": True,
            "response": "查询结果: 找到 3 条记录",
            "data": {"records": [{"id": 1}, {"id": 2}, {"id": 3}]}
        }

    # 注册 Skill
    tool = registry.register_skill(
        skill_name="sqlite-query",
        description="执行 SQLite 数据库查询",
        handler=execute_sqlite_query
    )

    # 执行工具
    result = asyncio.run(registry.execute(
        "skill.sqlite-query",
        user_input="查询所有用户",
        context={"session_id": "test"}
    ))

    print(f"Skill 执行结果: {result.response}")
    # 输出: Skill 执行结果: 查询结果: 找到 3 条记录


# ============================================================================
# 示例 3: 注册 MCP 工具
# ============================================================================

def example_mcp_tool():
    """示例 3: 注册 MCP 工具"""
    registry = ToolRegistry()

    # 模拟 MCP 工具执行函数
    async def call_filesystem_read(path: str) -> dict:
        return {
            "success": True,
            "data": f"文件内容: {path} 的内容..."
        }

    # 注册 MCP 工具
    tool = registry.register_mcp_tool(
        server_name="filesystem",
        tool_name="read_file",
        description="读取文件内容",
        handler=call_filesystem_read,
        parameters=[
            ToolParameter(
                name="path",
                type="string",
                description="文件路径",
                required=True
            )
        ]
    )

    # 执行工具
    result = asyncio.run(registry.execute(
        "mcp.filesystem.read_file",
        path="./test.txt"
    ))

    print(f"MCP 工具执行结果: {result.data}")
    # 输出: MCP 工具执行结果: 文件内容: ./test.txt 的内容...


# ============================================================================
# 示例 4: 注册 SubAgent 工具
# ============================================================================

def example_subagent_tool():
    """示例 4: 注册 SubAgent 工具"""
    registry = ToolRegistry()

    # 模拟 SubAgent 执行函数
    async def code_analyzer_process(query: str, context: dict = None) -> dict:
        return {
            "success": True,
            "response": f"代码分析完成: {query}",
            "data": {"issues": [], "suggestions": []}
        }

    # 注册 SubAgent
    tool = registry.register_subagent(
        agent_id="code-analyzer",
        description="代码分析专家",
        handler=code_analyzer_process,
        metadata={
            "version": "1.0",
            "capabilities": ["bug_detection", "code_review"]
        }
    )

    # 执行工具
    result = asyncio.run(registry.execute(
        "subagent.code-analyzer",
        query="分析这段代码的质量"
    ))

    print(f"SubAgent 执行结果: {result.response}")
    # 输出: SubAgent 执行结果: 代码分析完成: 分析这段代码的质量


# ============================================================================
# 示例 5: 查询和检索工具
# ============================================================================

def example_query_tools():
    """示例 5: 查询和检索工具"""
    registry = ToolRegistry()

    # 注册多个工具
    @registry.register("tool1")
    def func1():
        pass

    @registry.register("tool2")
    def func2():
        pass

    registry.register_skill("skill1", "Skill 1")
    registry.register_subagent("agent1", "Agent 1", lambda **kwargs: {"success": True})

    # 列出所有工具
    print("所有工具:")
    for tool in registry.list_tools():
        print(f"  - {tool.name} ({tool.type.value})")

    # 按类型过滤
    print("\n自定义工具:")
    for tool in registry.list_tools(type=ToolType.CUSTOM):
        print(f"  - {tool.name}")

    print("\nSkill 工具:")
    for tool in registry.list_tools(type=ToolType.SKILL):
        print(f"  - {tool.name}")

    # 统计
    print(f"\n工具总数: {registry.count()}")
    print(f"自定义工具: {registry.count(type=ToolType.CUSTOM)}")
    print(f"Skill 工具: {registry.count(type=ToolType.SKILL)}")
    print(f"SubAgent 工具: {registry.count(type=ToolType.SUBAGENT)}")


# ============================================================================
# 示例 6: 生成 OpenAPI Schema
# ============================================================================

def example_openapi_schema():
    """示例 6: 生成 OpenAPI Schema"""
    registry = ToolRegistry()

    @registry.register(
        "calculate",
        description="执行数学计算",
        parameters=[
            ToolParameter(name="x", type="number", description="第一个数", required=True),
            ToolParameter(name="y", type="number", description="第二个数", required=True),
            ToolParameter(name="operation", type="string", description="运算符", enum=["+", "-", "*", "/"])
        ]
    )
    def calculate(x: float, y: float, operation: str = "+") -> float:
        """执行数学计算"""
        if operation == "+":
            return x + y
        elif operation == "-":
            return x - y
        elif operation == "*":
            return x * y
        elif operation == "/":
            return x / y
        else:
            raise ValueError(f"未知运算符: {operation}")

    # 生成 OpenAPI Schema
    schema = registry.to_openapi_schema(group_by_type=True)

    import json
    print("OpenAPI Schema:")
    print(json.dumps(schema, indent=2, ensure_ascii=False))


# ============================================================================
# 示例 7: 启用/禁用工具
# ============================================================================

def example_enable_disable():
    """示例 7: 启用和禁用工具"""
    registry = ToolRegistry()

    @registry.register("test_tool")
    def test_func():
        return "test"

    print(f"工具默认状态: {'启用' if registry.get('test_tool').enabled else '禁用'}")

    # 禁用工具
    registry.disable("test_tool")
    print(f"禁用后状态: {'启用' if registry.get('test_tool').enabled else '禁用'}")

    # 尝试执行禁用的工具
    result = asyncio.run(registry.execute("test_tool"))
    print(f"执行结果: {result.error}")

    # 重新启用
    registry.enable("test_tool")
    print(f"重新启用后状态: {'启用' if registry.get('test_tool').enabled else '禁用'}")


# ============================================================================
# 示例 8: 使用全局注册表
# ============================================================================

def example_global_registry():
    """示例 8: 使用全局注册表"""
    from agent.tool_registry import get_global_registry, reset_global_registry

    # 重置全局注册表
    reset_global_registry()

    # 获取全局注册表
    registry = get_global_registry()

    @registry.register("global_tool")
    def global_func():
        return "global"

    # 在其他地方获取同一个注册表
    same_registry = get_global_registry()
    print(f"是否同一实例: {registry is same_registry}")
    print(f"工具存在: {'global_tool' in same_registry}")


# ============================================================================
# 主函数
# ============================================================================

def main():
    """运行所有示例"""
    print("=" * 60)
    print("ToolRegistry 使用示例")
    print("=" * 60)

    print("\n【示例 1】自定义工具")
    print("-" * 40)
    example_custom_tool()

    print("\n【示例 2】Skill 工具")
    print("-" * 40)
    example_skill_tool()

    print("\n【示例 3】MCP 工具")
    print("-" * 40)
    example_mcp_tool()

    print("\n【示例 4】SubAgent 工具")
    print("-" * 40)
    example_subagent_tool()

    print("\n【示例 5】查询和检索工具")
    print("-" * 40)
    example_query_tools()

    print("\n【示例 6】生成 OpenAPI Schema")
    print("-" * 40)
    example_openapi_schema()

    print("\n【示例 7】启用/禁用工具")
    print("-" * 40)
    example_enable_disable()

    print("\n【示例 8】使用全局注册表")
    print("-" * 40)
    example_global_registry()

    print("\n" + "=" * 60)
    print("所有示例运行完毕！")
    print("=" * 60)


if __name__ == "__main__":
    main()
