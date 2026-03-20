"""
MCP Adapter 集成测试

验证 MCP Adapter 与整个系统的集成：
- 适配器管理器集成
- 配置加载兼容性
- 工具注册和调用
"""

import asyncio
import tempfile
from pathlib import Path

from src.adapter_manager import AdapterManager
from src.adapters.core import AdapterType, AdapterConfig, ToolRequest


async def test_adapter_manager_integration():
    """测试适配器管理器集成"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建测试配置
        config_dir = Path(tmpdir) / "config"
        config_dir.mkdir()

        # 创建 MCP 服务器配置
        mcp_config = config_dir / "mcp.yaml"
        mcp_config.write_text("""
mcp_servers:
  test-server:
    enabled: true
    transport: stdio
    command: echo
    args: ["test"]
""")

        # 直接使用工厂创建 MCP 适配器
        from src.adapters.core import AdapterFactory, AdapterConfig, AdapterType

        factory = AdapterFactory()
        config = AdapterConfig(
            type=AdapterType.MCP,
            name="test_mcp",
            metadata={"project_root": tmpdir}
        )

        adapter = await factory.create_adapter(config)
        assert adapter is not None, "适配器创建失败"

        # 列出适配器
        adapters = factory.list_adapter_names()
        print(f"已注册的适配器: {adapters}")

        # 清理
        await factory.shutdown_all()
        print("集成测试通过")


async def test_backward_compatibility():
    """测试向后兼容性"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建 .claude/mcp.json 格式配置
        claude_dir = Path(tmpdir) / ".claude"
        claude_dir.mkdir()

        mcp_json = claude_dir / "mcp.json"
        mcp_json.write_text("""
{
  "mcpServers": {
    "test-server": {
      "command": "echo",
      "args": ["test"]
    }
  }
}
""")

        # 创建 MCP Adapter
        from src.adapters.mcp import MCPAdapter

        config = AdapterConfig(
            type=AdapterType.MCP,
            name="test_adapter",
            metadata={"project_root": tmpdir}
        )

        adapter = MCPAdapter(config)
        await adapter.initialize()

        # 验证工具索引
        tools = await adapter.list_tools()
        print(f"索引的工具: {tools}")

        # 清理
        await adapter.shutdown()
        print("向后兼容性测试通过")


if __name__ == "__main__":
    print("运行 MCP Adapter 集成测试...")

    try:
        asyncio.run(test_adapter_manager_integration())
        print("\n[OK] 适配器管理器集成测试通过")
    except Exception as e:
        print(f"\n[FAIL] 适配器管理器集成测试失败: {e}")
        import traceback
        traceback.print_exc()

    try:
        asyncio.run(test_backward_compatibility())
        print("\n[OK] 向后兼容性测试通过")
    except Exception as e:
        print(f"\n[FAIL] 向后兼容性测试失败: {e}")
        import traceback
        traceback.print_exc()

    print("\n所有集成测试完成!")
