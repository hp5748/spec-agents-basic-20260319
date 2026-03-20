"""
配置加载器 - 支持 .claude/ 和 register/ 两种配置目录

自动检测并加载多种格式的配置文件，确保向后兼容。
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


logger = logging.getLogger(__name__)


class ConfigFormat:
    """配置格式"""
    YAML = "yaml"
    JSON = "json"


class ConfigSource:
    """配置来源"""
    REGISTER = "register"
    CLAUDE = ".claude"
    USER = "~/.claude.json"


class ConfigLoader:
    """
    配置加载器

    支持多种配置格式的统一加载：
    - register/mcp.json (新增，最高优先级)
    - .claude/mcp.json (Claude Code 标准)
    - register/agents.json (新增)
    - .claude/agents.json (Claude Code 标准)
    - ~/.claude.json (用户级配置)
    """

    def __init__(
        self,
        project_root: Optional[str] = None,
        register_dir: str = "register",
        claude_dir: str = ".claude",
    ):
        self.project_root = Path(project_root or os.getcwd())
        self.register_dir = self.project_root / register_dir
        self.claude_dir = self.project_root / claude_dir
        self.user_config_path = Path.home() / ".claude.json"

    def load_mcp_config(self) -> Dict[str, Any]:
        """加载 MCP 配置（支持多种格式）"""
        configs = []

        # 按优先级加载（后面的会覆盖前面的）
        sources = [
            (self.user_config_path, "用户配置"),
            (self.claude_dir / "mcp.json", "Claude 目录"),
            (self.register_dir / "mcp.json", "Register 目录"),
            (self.register_dir / "mcp.yaml", "Register YAML"),
        ]

        for config_path, source_name in sources:
            if config_path.exists():
                logger.debug(f"加载配置: {config_path} ({source_name})")
                try:
                    if config_path.suffix in [".yaml", ".yml"]:
                        with open(config_path, "r", encoding="utf-8") as f:
                            config = yaml.safe_load(f) or {}
                            configs.append((config, source_name))
                    elif config_path.suffix == ".json":
                        with open(config_path, "r", encoding="utf-8") as f:
                            config = json.load(f)
                            # .claude.json 格式特殊处理
                            if config_path.name == ".claude.json":
                                config = {"mcpServers": config.get("mcpServers", {})}
                            configs.append((config, source_name))
                except Exception as e:
                    logger.warning(f"加载配置失败 {config_path}: {e}")

        # 合并配置（后面的覆盖前面的）
        merged = {}
        for config, source in configs:
            if "mcpServers" in config:
                merged.update(config["mcpServers"])
            elif isinstance(config, dict):
                merged.update(config)

        return {"mcpServers": merged}

    def load_agents_config(self) -> Dict[str, Any]:
        """加载 SubAgent 配置"""
        configs = []

        sources = [
            (self.claude_dir / "agents.json", "Claude 目录"),
            (self.register_dir / "agents.json", "Register 目录"),
            (self.register_dir / "agents.yaml", "Register YAML"),
        ]

        for config_path, source_name in sources:
            if config_path.exists():
                logger.debug(f"加载配置: {config_path} ({source_name})")
                try:
                    if config_path.suffix in [".yaml", ".yml"]:
                        with open(config_path, "r", encoding="utf-8") as f:
                            config = yaml.safe_load(f) or {}
                            configs.append((config, source_name))
                    elif config_path.suffix == ".json":
                        with open(config_path, "r", encoding="utf-8") as f:
                            config = json.load(f)
                            configs.append((config, source_name))
                except Exception as e:
                    logger.warning(f"加载配置失败 {config_path}: {e}")

        # 合并配置
        merged = {}
        for config, source in configs:
            if "subagents" in config:
                merged.update(config["subagents"])
            elif isinstance(config, dict):
                merged.update(config)

        return {"subagents": merged}

    def load_skills_config(self) -> Dict[str, Any]:
        """加载 Skills 配置"""
        configs = []

        sources = [
            (self.claude_dir / "skills.json", "Claude 目录"),
            (self.register_dir / "skills.json", "Register 目录"),
            (self.register_dir / "skills.yaml", "Register YAML"),
        ]

        for config_path, source_name in sources:
            if config_path.exists():
                logger.debug(f"加载配置: {config_path} ({source_name})")
                try:
                    if config_path.suffix in [".yaml", ".yml"]:
                        with open(config_path, "r", encoding="utf-8") as f:
                            config = yaml.safe_load(f) or {}
                            configs.append((config, source_name))
                    elif config_path.suffix == ".json":
                        with open(config_path, "r", encoding="utf-8") as f:
                            config = json.load(f)
                            configs.append((config, source_name))
                except Exception as e:
                    logger.warning(f"加载配置失败 {config_path}: {e}")

        # 合并配置
        merged = {}
        for config, source in configs:
            if isinstance(config, dict):
                merged.update(config)

        return merged

    def load_adapters_config(self) -> Dict[str, Any]:
        """加载适配器配置"""
        config_path = self.project_root / "config" / "adapters.yaml"
        if not config_path.exists():
            return {}

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"加载适配器配置失败 {config_path}: {e}")
            return {}

    def load_all_configs(self) -> Dict[str, Any]:
        """加载所有配置"""
        return {
            "mcp": self.load_mcp_config(),
            "agents": self.load_agents_config(),
            "skills": self.load_skills_config(),
            "adapters": self.load_adapters_config(),
        }

    def detect_config_sources(self) -> Dict[str, List[str]]:
        """检测所有配置来源"""
        sources = {
            "mcp": [],
            "agents": [],
            "skills": [],
        }

        # 检测 MCP 配置
        for path in [
            self.user_config_path,
            self.claude_dir / "mcp.json",
            self.register_dir / "mcp.json",
            self.register_dir / "mcp.yaml",
        ]:
            if path.exists():
                sources["mcp"].append(str(path))

        # 检测 Agents 配置
        for path in [
            self.claude_dir / "agents.json",
            self.register_dir / "agents.json",
            self.register_dir / "agents.yaml",
        ]:
            if path.exists():
                sources["agents"].append(str(path))

        # 检测 Skills 配置
        for path in [
            self.claude_dir / "skills.json",
            self.register_dir / "skills.json",
            self.register_dir / "skills.yaml",
        ]:
            if path.exists():
                sources["skills"].append(str(path))

        return sources

    def should_migrate(self) -> Tuple[bool, List[str]]:
        """检查是否需要迁移配置"""
        reasons = []

        # 检查是否使用了旧配置目录
        claude_configs = list(self.claude_dir.glob("*.json"))
        if claude_configs:
            reasons.append(f".claude/ 目录中有 {len(claude_configs)} 个 JSON 配置文件")

        # 检查是否没有使用新配置目录
        if not self.register_dir.exists():
            reasons.append("register/ 目录不存在，建议创建")

        return len(reasons) > 0, reasons


def get_config_loader(project_root: Optional[str] = None) -> ConfigLoader:
    """获取配置加载器实例"""
    return ConfigLoader(project_root=project_root)


def load_all_configs(project_root: Optional[str] = None) -> Dict[str, Any]:
    """便捷函数：加载所有配置"""
    loader = get_config_loader(project_root)
    return loader.load_all_configs()
