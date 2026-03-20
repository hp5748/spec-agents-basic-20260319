"""
MCP 配置加载器

支持多种配置格式，按优先级加载：
1. config/mcp.yaml (项目 YAML 配置，最高优先级)
2. .claude/mcp.json (Claude Code 标准)
3. ~/.claude.json (用户级配置)

配置格式详见 config/mcp.yaml
"""

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """MCP Server 配置"""
    name: str

    # 传输配置
    transport: str = "stdio"           # stdio / http / sse

    # STDIO 传输
    command: Optional[str] = None
    args: List[str] = field(default_factory=list)

    # HTTP/SSE 传输
    url: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)

    # 通用配置
    env: Dict[str, str] = field(default_factory=dict)
    disabled: bool = False

    # 运行时状态
    _process: Any = None                # 子进程对象
    _status: str = "stopped"            # stopped / starting / running / error


@dataclass
class MCPConfig:
    """MCP 配置集合"""
    yaml_level: Dict[str, MCPServerConfig] = field(default_factory=dict)  # config/mcp.yaml
    project_level: Dict[str, MCPServerConfig] = field(default_factory=dict)  # .claude/mcp.json
    user_level: Dict[str, MCPServerConfig] = field(default_factory=dict)  # ~/.claude.json

    def get_all_servers(self) -> Dict[str, MCPServerConfig]:
        """获取所有服务器配置（优先级：yaml > project > user）"""
        all_servers = {}
        all_servers.update(self.user_level)
        all_servers.update(self.project_level)
        all_servers.update(self.yaml_level)  # 最高优先级
        return all_servers


class MCPConfigLoader:
    """
    MCP 配置加载器

    支持多种配置格式，按优先级加载：
    1. config/mcp.yaml (项目 YAML 配置)
    2. .claude/mcp.json (Claude Code 标准)
    3. ~/.claude.json (用户级配置)
    """

    def __init__(self, project_root: str = "."):
        self._project_root = Path(project_root).resolve()
        self._yaml_config_path = self._project_root / "config" / "mcp.yaml"
        self._project_config_path = self._project_root / ".claude" / "mcp.json"
        self._user_config_path = Path.home() / ".claude.json"

    def load(self) -> MCPConfig:
        """加载所有配置（优先级：yaml > project > user）"""
        config = MCPConfig()

        # 1. 加载 YAML 配置（最高优先级）
        if YAML_AVAILABLE and self._yaml_config_path.exists():
            try:
                config.yaml_level = self._load_yaml_config()
            except Exception as e:
                logger.warning(f"加载 YAML MCP 配置失败: {e}")

        # 2. 加载项目级 JSON 配置
        if self._project_config_path.exists():
            try:
                project_data = json.loads(self._project_config_path.read_text(encoding="utf-8"))
                if "mcpServers" in project_data:
                    for name, server_data in project_data["mcpServers"].items():
                        config.project_level[name] = self._parse_server_config(name, server_data)
                    logger.info(f"已加载项目级 MCP 配置: {len(config.project_level)} 个服务器")
            except Exception as e:
                logger.warning(f"加载项目级 MCP 配置失败: {e}")

        # 3. 加载用户级配置
        if self._user_config_path.exists():
            try:
                user_data = json.loads(self._user_config_path.read_text(encoding="utf-8"))
                if "mcpServers" in user_data:
                    for name, server_data in user_data["mcpServers"].items():
                        config.user_level[name] = self._parse_server_config(name, server_data)
                    logger.info(f"已加载用户级 MCP 配置: {len(config.user_level)} 个服务器")
            except Exception as e:
                logger.warning(f"加载用户级 MCP 配置失败: {e}")

        return config

    def _load_yaml_config(self) -> Dict[str, MCPServerConfig]:
        """加载 YAML 格式的 MCP 配置"""
        yaml_data = yaml.safe_load(self._yaml_config_path.read_text(encoding="utf-8"))

        if not yaml_data or "mcp_servers" not in yaml_data:
            logger.warning(f"YAML 配置缺少 mcp_servers 节点: {self._yaml_config_path}")
            return {}

        servers = {}
        for name, server_data in yaml_data["mcp_servers"].items():
            # 检查是否启用
            if not server_data.get("enabled", True):
                logger.debug(f"YAML 配置中服务器 {name} 已禁用，跳过")
                continue

            # 转换 YAML 格式到内部格式
            servers[name] = self._parse_yaml_server_config(name, server_data)

        logger.info(f"已加载 YAML MCP 配置: {len(servers)} 个服务器")
        return servers

    def _parse_yaml_server_config(self, name: str, data: Dict[str, Any]) -> MCPServerConfig:
        """解析 YAML 格式的单个服务器配置"""
        # 环境变量展开
        env = data.get("env", {})
        expanded_env = {}
        for key, value in env.items():
            if isinstance(value, str) and value.startswith("$"):
                var_name = value[1:]
                expanded_env[key] = os.getenv(var_name, value)
            else:
                expanded_env[key] = value

        # 判断传输方式
        transport = data.get("transport", "stdio")

        if transport == "http" or transport == "sse":
            # HTTP/SSE 传输
            return MCPServerConfig(
                name=name,
                transport=transport,
                url=data.get("url"),
                headers=data.get("headers", {}),
                env=expanded_env,
                disabled=not data.get("enabled", True)
            )
        else:
            # STDIO 传输（默认）
            command = data.get("command")
            args = data.get("args", [])

            return MCPServerConfig(
                name=name,
                transport="stdio",
                command=command,
                args=args,
                env=expanded_env,
                disabled=not data.get("enabled", True)
            )

    def _parse_server_config(self, name: str, data: Dict[str, Any]) -> MCPServerConfig:
        """解析单个服务器配置"""
        # 环境变量展开
        env = data.get("env", {})
        expanded_env = {}
        for key, value in env.items():
            if isinstance(value, str) and value.startswith("$"):
                var_name = value[1:]
                expanded_env[key] = os.getenv(var_name, value)
            else:
                expanded_env[key] = value

        # 判断传输方式
        if "url" in data:
            # HTTP/SSE 传输
            return MCPServerConfig(
                name=name,
                transport=data.get("transport", "http"),
                url=data["url"],
                headers=data.get("headers", {}),
                env=expanded_env,
                disabled=data.get("disabled", False)
            )
        else:
            # STDIO 传输
            return MCPServerConfig(
                name=name,
                transport="stdio",
                command=data["command"],
                args=data.get("args", []),
                env=expanded_env,
                disabled=data.get("disabled", False)
            )

    async def save_project_config(self, servers: Dict[str, Dict[str, Any]]) -> None:
        """保存项目级配置"""
        self._project_config_path.parent.mkdir(parents=True, exist_ok=True)

        config_data = {
            "$schema": "https://json.schemastore.org/claude-mcp.json",
            "mcpServers": servers
        }

        self._project_config_path.write_text(
            json.dumps(config_data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        logger.info(f"MCP 配置已保存到: {self._project_config_path}")

    def list_available_servers(self) -> List[str]:
        """列出所有可用的服务器配置"""
        config = self.load()
        return list(config.get_all_servers().keys())
