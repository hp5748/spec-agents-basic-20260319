"""
SubAgent 配置加载器

支持两种配置格式：
1. .claude/agents.json - Claude Code 标准
2. register/agents.json - 自定义注册格式
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


class SubAgentConfigLoader:
    """
    SubAgent 配置加载器

    支持从多个路径加载配置，自动合并配置项。
    """

    def __init__(self, project_root: str = "."):
        self._project_root = Path(project_root).resolve()
        self._config_paths = [
            self._project_root / ".claude" / "agents.json",
            self._project_root / "register" / "agents.json",
        ]

    def load_config(self) -> Dict[str, Any]:
        """
        加载配置（合并所有可用配置）

        Returns:
            Dict[str, Any]: 合并后的配置
        """
        merged_config = {"subagents": {}}

        for config_path in self._config_paths:
            if not config_path.exists():
                logger.debug(f"配置文件不存在: {config_path}")
                continue

            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)

                # 合并 subagents
                if "subagents" in config:
                    merged_config["subagents"].update(config["subagents"])
                    logger.info(f"已加载配置: {config_path}")

            except Exception as e:
                logger.warning(f"加载配置失败 {config_path}: {e}")

        return merged_config

    def load_from_claude_format(self) -> Dict[str, Any]:
        """
        从 .claude/agents.json 加载配置

        Returns:
            Dict[str, Any]: 配置字典
        """
        config_path = self._project_root / ".claude" / "agents.json"

        if not config_path.exists():
            return {"subagents": {}}

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            logger.info(f"已加载 .claude/agents.json")
            return config
        except Exception as e:
            logger.error(f"加载 .claude/agents.json 失败: {e}")
            return {"subagents": {}}

    def load_from_register_format(self) -> Dict[str, Any]:
        """
        从 register/agents.json 加载配置

        Returns:
            Dict[str, Any]: 配置字典
        """
        config_path = self._project_root / "register" / "agents.json"

        if not config_path.exists():
            return {"subagents": {}}

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            logger.info(f"已加载 register/agents.json")
            return config
        except Exception as e:
            logger.error(f"加载 register/agents.json 失败: {e}")
            return {"subagents": {}}

    def get_enabled_agents(self) -> List[str]:
        """
        获取所有启用的 Agent 名称

        Returns:
            List[str]: Agent 名称列表
        """
        config = self.load_config()
        enabled = []

        for name, agent_config in config.get("subagents", {}).items():
            if agent_config.get("enabled", True):
                enabled.append(name)

        return enabled

    def get_agent_config(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        获取特定 Agent 的配置

        Args:
            agent_name: Agent 名称

        Returns:
            Optional[Dict[str, Any]]: Agent 配置，不存在则返回 None
        """
        config = self.load_config()
        return config.get("subagents", {}).get(agent_name)

    def save_to_claude_format(self, config: Dict[str, Any]) -> bool:
        """
        保存配置到 .claude/agents.json

        Args:
            config: 配置字典

        Returns:
            bool: 是否成功
        """
        config_path = self._project_root / ".claude" / "agents.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            logger.info(f"已保存配置到 .claude/agents.json")
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False

    def save_to_register_format(self, config: Dict[str, Any]) -> bool:
        """
        保存配置到 register/agents.json

        Args:
            config: 配置字典

        Returns:
            bool: 是否成功
        """
        config_path = self._project_root / "register" / "agents.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            logger.info(f"已保存配置到 register/agents.json")
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False


class AgentContext:
    """
    Agent 上下文

    用于在主 Agent 和 SubAgent 之间共享状态。
    """

    def __init__(self, session_id: str = ""):
        self.session_id = session_id
        self._state: Dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        """设置上下文值"""
        self._state[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """获取上下文值"""
        return self._state.get(key, default)

    def update(self, data: Dict[str, Any]) -> None:
        """批量更新上下文"""
        self._state.update(data)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "state": self._state.copy()
        }

    def clear(self) -> None:
        """清空上下文"""
        self._state.clear()


class SharedContextManager:
    """
    共享上下文管理器

    管理多个 Agent 之间的上下文共享。
    """

    def __init__(self):
        self._contexts: Dict[str, AgentContext] = {}

    def get_context(self, session_id: str) -> AgentContext:
        """
        获取会话上下文（不存在则创建）

        Args:
            session_id: 会话 ID

        Returns:
            AgentContext: 上下文对象
        """
        if session_id not in self._contexts:
            self._contexts[session_id] = AgentContext(session_id)
        return self._contexts[session_id]

    def remove_context(self, session_id: str) -> None:
        """
        移除会话上下文

        Args:
            session_id: 会话 ID
        """
        if session_id in self._contexts:
            del self._contexts[session_id]

    def clear_all(self) -> None:
        """清空所有上下文"""
        self._contexts.clear()
