"""
配置加载器单元测试
"""

import json
import pytest
import tempfile
from pathlib import Path

from src.config.loader import ConfigLoader, ConfigFormat, ConfigSource
from src.config.migrator import ConfigMigrator, migrate_configs, should_migrate


class TestConfigLoader:
    """ConfigLoader 测试"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def loader(self, temp_dir):
        """创建配置加载器"""
        return ConfigLoader(project_root=str(temp_dir))

    def test_init(self, temp_dir):
        """测试初始化"""
        loader = ConfigLoader(project_root=str(temp_dir))

        assert loader.project_root == temp_dir
        assert loader.register_dir == temp_dir / "register"
        assert loader.claude_dir == temp_dir / ".claude"

    def test_load_mcp_config_from_claude_dir(self, temp_dir):
        """测试从 .claude 目录加载 MCP 配置"""
        # 创建配置
        claude_dir = temp_dir / ".claude"
        claude_dir.mkdir(parents=True)
        mcp_config = claude_dir / "mcp.json"
        mcp_config.write_text(
            json.dumps({"mcpServers": {"test": {"command": "test"}}}),
            encoding="utf-8",
        )

        loader = ConfigLoader(project_root=str(temp_dir))
        config = loader.load_mcp_config()

        assert "mcpServers" in config
        assert "test" in config["mcpServers"]

    def test_load_mcp_config_from_register_dir(self, temp_dir):
        """测试从 register 目录加载 MCP 配置"""
        # 创建配置
        register_dir = temp_dir / "register"
        register_dir.mkdir(parents=True)
        mcp_config = register_dir / "mcp.json"
        mcp_config.write_text(
            json.dumps({"mcpServers": {"test2": {"command": "test2"}}}),
            encoding="utf-8",
        )

        loader = ConfigLoader(project_root=str(temp_dir))
        config = loader.load_mcp_config()

        assert "mcpServers" in config
        assert "test2" in config["mcpServers"]

    def test_config_merge(self, temp_dir):
        """测试配置合并（register 覆盖 .claude）"""
        # 创建 .claude 配置
        claude_dir = temp_dir / ".claude"
        claude_dir.mkdir(parents=True)
        mcp_config1 = claude_dir / "mcp.json"
        mcp_config1.write_text(
            json.dumps({"mcpServers": {"server1": {"cmd": "a"}, "server2": {"cmd": "b"}}}),
            encoding="utf-8",
        )

        # 创建 register 配置（覆盖 server2）
        register_dir = temp_dir / "register"
        register_dir.mkdir(parents=True)
        mcp_config2 = register_dir / "mcp.json"
        mcp_config2.write_text(
            json.dumps({"mcpServers": {"server2": {"cmd": "c"}, "server3": {"cmd": "d"}}}),
            encoding="utf-8",
        )

        loader = ConfigLoader(project_root=str(temp_dir))
        config = loader.load_mcp_config()

        # server1 来自 .claude
        assert config["mcpServers"]["server1"]["cmd"] == "a"
        # server2 被 register 覆盖
        assert config["mcpServers"]["server2"]["cmd"] == "c"
        # server3 来自 register
        assert config["mcpServers"]["server3"]["cmd"] == "d"

    def test_load_agents_config(self, temp_dir):
        """测试加载 Agents 配置"""
        register_dir = temp_dir / "register"
        register_dir.mkdir(parents=True)
        agents_config = register_dir / "agents.json"
        agents_config.write_text(
            json.dumps({"subagents": {"agent1": {"name": "test"}}}),
            encoding="utf-8",
        )

        loader = ConfigLoader(project_root=str(temp_dir))
        config = loader.load_agents_config()

        assert "subagents" in config
        assert "agent1" in config["subagents"]

    def test_load_all_configs(self, temp_dir):
        """测试加载所有配置"""
        register_dir = temp_dir / "register"
        register_dir.mkdir(parents=True)

        # 创建多个配置文件
        (register_dir / "mcp.json").write_text(
            json.dumps({"mcpServers": {}}), encoding="utf-8"
        )
        (register_dir / "agents.json").write_text(
            json.dumps({"subagents": {}}), encoding="utf-8"
        )

        loader = ConfigLoader(project_root=str(temp_dir))
        configs = loader.load_all_configs()

        assert "mcp" in configs
        assert "agents" in configs
        assert "skills" in configs
        assert "adapters" in configs

    def test_detect_config_sources(self, temp_dir):
        """测试检测配置来源"""
        claude_dir = temp_dir / ".claude"
        claude_dir.mkdir(parents=True)
        (claude_dir / "mcp.json").write_text("{}", encoding="utf-8")

        loader = ConfigLoader(project_root=str(temp_dir))
        sources = loader.detect_config_sources()

        assert "mcp" in sources
        assert len(sources["mcp"]) > 0

    def test_should_migrate(self, temp_dir):
        """测试是否需要迁移"""
        claude_dir = temp_dir / ".claude"
        claude_dir.mkdir(parents=True)
        (claude_dir / "mcp.json").write_text("{}", encoding="utf-8")

        loader = ConfigLoader(project_root=str(temp_dir))
        need_migrate, reasons = loader.should_migrate()

        assert need_migrate is True
        assert len(reasons) > 0


class TestConfigMigrator:
    """ConfigMigrator 测试"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def migrator(self, temp_dir):
        """创建迁移器"""
        return ConfigMigrator(project_root=str(temp_dir))

    def test_init(self, temp_dir):
        """测试初始化"""
        migrator = ConfigMigrator(project_root=str(temp_dir))

        assert migrator.register_dir == temp_dir / "register"

    def test_migrate_with_dry_run(self, temp_dir):
        """测试模拟迁移"""
        # 创建源配置
        claude_dir = temp_dir / ".claude"
        claude_dir.mkdir(parents=True)
        (claude_dir / "mcp.json").write_text(
            json.dumps({"mcpServers": {"test": {}}}), encoding="utf-8"
        )

        migrator = ConfigMigrator(project_root=str(temp_dir))
        result = migrator.migrate(dry_run=True)

        assert result["success"] is True
        assert len(result["migrated"]) > 0
        # dry run 不会创建文件
        assert not (temp_dir / "register" / "mcp.json").exists()

    def test_migrate_actual(self, temp_dir):
        """测试实际迁移"""
        # 创建源配置
        claude_dir = temp_dir / ".claude"
        claude_dir.mkdir(parents=True)
        (claude_dir / "mcp.json").write_text(
            json.dumps({"mcpServers": {"test": {}}}), encoding="utf-8"
        )

        migrator = ConfigMigrator(project_root=str(temp_dir))
        result = migrator.migrate(backup=False, dry_run=False)

        assert result["success"] is True
        # 检查文件已创建
        assert (temp_dir / "register" / "mcp.json").exists()

    def test_validate_migration(self, temp_dir):
        """测试验证迁移"""
        # 创建配置
        register_dir = temp_dir / "register"
        register_dir.mkdir(parents=True)
        (register_dir / "mcp.json").write_text(
            json.dumps({"mcpServers": {}}), encoding="utf-8"
        )

        migrator = ConfigMigrator(project_root=str(temp_dir))
        result = migrator.validate_migration()

        assert result["valid"] is True


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_should_migrate_function(self, tmpdir):
        """测试 should_migrate 函数"""
        claude_dir = Path(tmpdir) / ".claude"
        claude_dir.mkdir()
        (claude_dir / "mcp.json").write_text("{}", encoding="utf-8")

        need_migrate, reasons = should_migrate(str(tmpdir))

        assert need_migrate is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
