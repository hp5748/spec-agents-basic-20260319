"""
MCP Adapter 测试

测试 MCP 适配器的核心功能：
- 配置加载（YAML 和 JSON 格式）
- 适配器初始化
- 工具索引和注册
- 工具调用执行
- 错误处理
"""

import asyncio
import pytest
import tempfile
from pathlib import Path

from src.adapters.core import (
    AdapterFactory,
    AdapterType,
    AdapterConfig,
    ToolRequest,
    ToolResponse
)
from src.adapters.mcp import MCPAdapter, MCPConfigLoader


class TestMCPConfigLoader:
    """测试 MCP 配置加载器"""

    def test_load_yaml_config(self):
        """测试加载 YAML 配置"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试配置
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            config_file = config_dir / "mcp.yaml"

            config_content = """
mcp_servers:
  test-server:
    enabled: true
    transport: stdio
    command: echo
    args: ["test"]
    env:
      TEST_VAR: "value"
"""
            config_file.write_text(config_content)

            # 加载配置
            loader = MCPConfigLoader(project_root=tmpdir)
            config = loader.load()

            # 验证
            assert len(config.yaml_level) == 1
            assert "test-server" in config.yaml_level

            server_config = config.yaml_level["test-server"]
            assert server_config.name == "test-server"
            assert server_config.transport == "stdio"
            assert server_config.command == "echo"
            assert server_config.args == ["test"]
            assert server_config.env == {"TEST_VAR": "value"}
            assert not server_config.disabled

    def test_load_json_config(self):
        """测试加载 JSON 配置"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建 .claude/mcp.json
            claude_dir = Path(tmpdir) / ".claude"
            claude_dir.mkdir()
            config_file = claude_dir / "mcp.json"

            config_content = """
{
  "mcpServers": {
    "test-server": {
      "command": "echo",
      "args": ["test"]
    }
  }
}
"""
            config_file.write_text(config_content)

            # 加载配置
            loader = MCPConfigLoader(project_root=tmpdir)
            config = loader.load()

            # 验证
            assert len(config.project_level) == 1
            assert "test-server" in config.project_level

            server_config = config.project_level["test-server"]
            assert server_config.name == "test-server"
            assert server_config.transport == "stdio"
            assert server_config.command == "echo"

    def test_config_priority(self):
        """测试配置优先级（YAML > JSON）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建 YAML 配置
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            yaml_file = config_dir / "mcp.yaml"
            yaml_file.write_text("""
mcp_servers:
  test-server:
    enabled: true
    transport: stdio
    command: echo-from-yaml
    args: ["yaml"]
""")

            # 创建 JSON 配置
            claude_dir = Path(tmpdir) / ".claude"
            claude_dir.mkdir()
            json_file = claude_dir / "mcp.json"
            json_file.write_text("""
{
  "mcpServers": {
    "test-server": {
      "command": "echo-from-json",
      "args": ["json"]
    }
  }
}
""")

            # 加载配置
            loader = MCPConfigLoader(project_root=tmpdir)
            config = loader.load()

            # 验证优先级
            all_servers = config.get_all_servers()
            assert "test-server" in all_servers
            # YAML 优先级更高
            assert all_servers["test-server"].command == "echo-from-yaml"


class TestMCPAdapter:
    """测试 MCP 适配器"""

    @pytest.mark.asyncio
    async def test_adapter_initialization(self):
        """测试适配器初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试配置
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            config_file = config_dir / "mcp.yaml"
            config_file.write_text("""
mcp_servers:
  test-server:
    enabled: true
    transport: stdio
    command: echo
    args: ["test"]
""")

            # 创建适配器
            adapter_config = AdapterConfig(
                type=AdapterType.MCP,
                name="test_mcp_adapter",
                metadata={"project_root": tmpdir}
            )

            adapter = MCPAdapter(adapter_config)

            # 初始化
            await adapter.initialize()

            # 验证
            assert adapter.is_enabled()
            capabilities = adapter.get_capabilities()
            assert capabilities.supports_async
            assert capabilities.supports_batch

            # 清理
            await adapter.shutdown()

    @pytest.mark.asyncio
    async def test_tool_indexing(self):
        """测试工具索引"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试配置（使用 SQLite 作为示例）
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            config_file = config_dir / "mcp.yaml"

            # 使用 echo 模拟 MCP 服务器
            config_file.write_text("""
mcp_servers:
  mock-server:
    enabled: true
    transport: stdio
    command: echo
    args: ["mock"]
""")

            # 创建适配器
            adapter_config = AdapterConfig(
                type=AdapterType.MCP,
                name="test_mcp_adapter",
                metadata={"project_root": tmpdir}
            )

            adapter = MCPAdapter(adapter_config)
            await adapter.initialize()

            # 列出工具
            tools = await adapter.list_tools()
            assert isinstance(tools, list)

            # 清理
            await adapter.shutdown()

    @pytest.mark.asyncio
    async def test_execute_request(self):
        """测试执行工具调用"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试配置
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            config_file = config_dir / "mcp.yaml"
            config_file.write_text("""
mcp_servers:
  test-server:
    enabled: true
    transport: stdio
    command: echo
    args: ["test"]
""")

            # 创建适配器
            adapter_config = AdapterConfig(
                type=AdapterType.MCP,
                name="test_mcp_adapter",
                metadata={"project_root": tmpdir}
            )

            adapter = MCPAdapter(adapter_config)
            await adapter.initialize()

            # 测试无效的工具调用
            request = ToolRequest(
                tool_name="non_existent_tool",
                parameters={}
            )

            response = await adapter.execute(request)
            assert not response.success
            assert "not found" in response.error.lower()

            # 清理
            await adapter.shutdown()


class TestMCPIntegration:
    """测试 MCP 集成"""

    @pytest.mark.asyncio
    async def test_factory_registration(self):
        """测试工厂注册"""
        factory = AdapterFactory()

        # 验证 MCP 类型已注册
        assert AdapterType.MCP in factory._adapter_classes

    @pytest.mark.asyncio
    async def test_factory_create(self):
        """测试工厂创建适配器"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试配置
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            config_file = config_dir / "mcp.yaml"
            config_file.write_text("""
mcp_servers:
  test-server:
    enabled: true
    transport: stdio
    command: echo
    args: ["test"]
""")

            # 使用工厂创建
            factory = AdapterFactory()
            config = AdapterConfig(
                type=AdapterType.MCP,
                name="test_mcp_adapter",
                metadata={"project_root": tmpdir}
            )

            adapter = await factory.create_adapter(config)

            # 验证
            assert adapter is not None
            assert adapter.config.name == "test_mcp_adapter"

            # 清理
            await factory.shutdown_all()


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
