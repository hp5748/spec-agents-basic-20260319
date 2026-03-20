"""
SubAgent 基类

所有 SubAgent 必须继承此类并实现核心方法。
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional


logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Agent 运行时配置"""
    name: str
    display_name: str
    description: str
    can_stream: bool = True
    can_use_tools: bool = True
    can_delegate: bool = False
    timeout: int = 60
    requires_approval: bool = False


@dataclass
class SubAgentInput:
    """SubAgent 输入"""
    query: str
    context: Dict[str, Any] = field(default_factory=dict)
    session_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SubAgentOutput:
    """SubAgent 输出"""
    success: bool
    response: str
    data: Dict[str, Any] = field(default_factory=dict)
    agent_id: str = ""
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    # 调用链追踪字段
    source_type: str = "subagent"
    chain_info: List[str] = field(default_factory=list)


class SubAgent(ABC):
    """
    SubAgent 基类

    所有 SubAgent 必须继承此类。

    实现 "Agents as Tools" 模式。
    """

    def __init__(
        self,
        agent_id: str,
        config: AgentConfig,
        llm_client: Optional[Any] = None
    ):
        self.agent_id = agent_id
        self.config = config
        self._llm_client = llm_client
        self._tools: Dict[str, Callable] = {}
        self._system_prompt = ""

    @abstractmethod
    async def process(
        self,
        input_data: SubAgentInput
    ) -> SubAgentOutput:
        """
        处理输入并返回输出

        这是 SubAgent 的核心方法。
        """
        pass

    async def process_stream(
        self,
        input_data: SubAgentInput
    ) -> AsyncGenerator[str, None]:
        """
        流式处理（可选实现）

        默认实现：调用 process() 并逐字符输出
        """
        output = await self.process(input_data)
        for char in output.response:
            yield char

    @abstractmethod
    def can_handle(self, input_data: SubAgentInput) -> float:
        """
        判断是否能处理此输入

        返回置信度 0.0-1.0
        """
        pass

    def register_tool(self, name: str, handler: Callable) -> None:
        """注册工具"""
        self._tools[name] = handler

    def set_system_prompt(self, prompt: str) -> None:
        """设置系统提示词"""
        self._system_prompt = prompt

    async def delegate_to(
        self,
        agent_name: str,
        input_data: SubAgentInput
    ) -> SubAgentOutput:
        """
        委托给其他 SubAgent

        仅当 config.can_delegate = True 时可用
        """
        if not self.config.can_delegate:
            raise ValueError(f"{self.agent_id} cannot delegate to other agents")

        # 实现委托逻辑（需要 orchestrator 支持）
        raise NotImplementedError("委托功能需要通过 Orchestrator 实现")
