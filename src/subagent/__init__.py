"""
SubAgent 模块

支持多 Agent 协作，包括：
- Agent 路由（基于关键词和意图）
- 并行执行
- 链式调用

SubAgent 通过扫描 subagents/ 目录自动发现，无需手动注册。
"""

from .config import SubAgentLoader, SubAgentScanner
from .base_agent import SubAgent, SubAgentInput, SubAgentOutput, AgentConfig
from .orchestrator import SubAgentOrchestrator

__all__ = [
    "SubAgentLoader",
    "SubAgentScanner",
    "SubAgent",
    "SubAgentInput",
    "SubAgentOutput",
    "AgentConfig",
    "SubAgentOrchestrator",
]
