"""
SubAgent 配置加载器

扫描 subagents/ 目录，自动发现可用的 Agent。
"""

import importlib.util
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base_agent import SubAgent, AgentConfig


logger = logging.getLogger(__name__)


@dataclass
class DiscoveredAgent:
    """发现的 Agent 信息"""
    name: str
    entry_path: str
    description: str = ""
    enabled: bool = True


class SubAgentScanner:
    """
    SubAgent 扫描器

    扫描 subagents/ 目录，自动发现可用的 Agent。
    """

    def __init__(self, project_root: str = ".", subagents_dir: str = "subagents"):
        self._subagents_dir = Path(project_root) / subagents_dir

    def scan(self) -> Dict[str, DiscoveredAgent]:
        """
        扫描 subagents 目录

        Returns:
            Dict[str, DiscoveredAgent]: {agent_name: agent_info}
        """
        if not self._subagents_dir.exists():
            logger.info(f"SubAgents 目录不存在: {self._subagents_dir}")
            return {}

        agents = {}

        for agent_dir in self._subagents_dir.iterdir():
            # 跳过非目录和隐藏目录
            if not agent_dir.is_dir() or agent_dir.name.startswith("_"):
                continue

            # 检查是否有 agent.py
            agent_file = agent_dir / "agent.py"
            if not agent_file.exists():
                logger.debug(f"跳过 {agent_dir.name}: 没有 agent.py")
                continue

            # 读取描述（如果有）
            description = self._read_agent_description(agent_dir)

            agents[agent_dir.name] = DiscoveredAgent(
                name=agent_dir.name,
                entry_path=str(agent_file),
                description=description,
                enabled=True
            )

            logger.info(f"发现 Agent: {agent_dir.name}")

        return agents

    def _read_agent_description(self, agent_dir: Path) -> str:
        """读取 Agent 描述"""
        # 优先从 AGENT.md 读取
        agent_md = agent_dir / "AGENT.md"
        if agent_md.exists():
            try:
                content = agent_md.read_text(encoding="utf-8")
                # 提取第一行或第一段
                lines = content.strip().split("\n")
                for line in lines[:5]:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        return line
            except Exception:
                pass

        # 其次从 prompts/system.md 读取
        system_md = agent_dir / "prompts" / "system.md"
        if system_md.exists():
            try:
                content = system_md.read_text(encoding="utf-8")
                lines = content.strip().split("\n")
                for line in lines[:5]:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        return line
            except Exception:
                pass

        # 默认描述
        return f"{agent_dir.name} Agent"


class SubAgentLoader:
    """
    SubAgent 加载器

    从扫描结果加载 Agent 类。
    """

    def __init__(self, project_root: str = "."):
        self._project_root = Path(project_root).resolve()
        self._scanner = SubAgentScanner(project_root)

    def scan_and_load(
        self,
        llm_client: Optional[Any] = None
    ) -> Dict[str, SubAgent]:
        """
        扫描并加载所有 Agents

        Args:
            llm_client: LLM 客户端（可选）

        Returns:
            Dict[str, SubAgent]: {agent_name: agent_instance}
        """
        discovered = self._scanner.scan()
        agents = {}

        for name, info in discovered.items():
            if not info.enabled:
                continue

            agent = self._load_agent(name, info, llm_client)
            if agent:
                agents[name] = agent

        return agents

    def _load_agent(
        self,
        name: str,
        info: DiscoveredAgent,
        llm_client: Optional[Any] = None
    ) -> Optional[SubAgent]:
        """加载指定 Agent"""
        try:
            # 动态加载模块
            spec = importlib.util.spec_from_file_location(
                f"subagents.{name}",
                info.entry_path
            )
            if not spec or not spec.loader:
                logger.error(f"无法加载模块: {info.entry_path}")
                return None

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 获取 Agent 类
            if hasattr(module, "Agent"):
                AgentClass = module.Agent
            else:
                logger.error(f"{info.entry_path} 中未找到 Agent 类")
                return None

            # 创建配置对象
            agent_config = AgentConfig(
                name=name,
                display_name=info.description,
                description=info.description
            )

            # 实例化
            agent = AgentClass(name, agent_config, llm_client)

            logger.info(f"已加载 Agent: {name}")
            return agent

        except Exception as e:
            logger.error(f"加载 Agent {name} 失败: {e}")
            return None

    def list_available_agents(self) -> List[str]:
        """列出所有可用的 Agent"""
        discovered = self._scanner.scan()
        return [name for name, info in discovered.items() if info.enabled]
