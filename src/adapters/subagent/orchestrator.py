"""
SubAgent 编排器（适配器版本）

负责：
- 管理 SubAgent 生命周期
- 路由任务到合适的 Agent
- 协调多个 Agent 并行执行
- 聚合 Agent 返回结果
- 支持上下文共享
"""

import asyncio
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from .config import SharedContextManager, AgentContext
from ..core.types import AdapterType


logger = logging.getLogger(__name__)


# 导入原始的 SubAgent 相关类
import sys
sys.path.insert(0, str(__file__).replace("src/adapters/subagent/orchestrator.py", ""))

try:
    from src.subagent.config import SubAgentLoader, DiscoveredAgent
    from src.subagent.base_agent import SubAgent, SubAgentInput, SubAgentOutput
except ImportError:
    # 相对导入
    from ...subagent.config import SubAgentLoader, DiscoveredAgent
    from ...subagent.base_agent import SubAgent, SubAgentInput, SubAgentOutput


class SubAgentOrchestrator:
    """
    SubAgent 编排器（适配器版本）

    使用方式：
        orchestrator = SubAgentOrchestrator()
        await orchestrator.initialize()

        # 路由到最合适的 Agent
        result = await orchestrator.route(input_data)

        # 并行执行多个 Agents
        results = await orchestrator.route_parallel(input_data, max_agents=3)

        # 链式调用
        result = await orchestrator.chain(input_data, ["agent1", "agent2"])
    """

    def __init__(
        self,
        project_root: str = ".",
        llm_client: Optional[Any] = None,
        shared_context: Optional[SharedContextManager] = None
    ):
        self._project_root = project_root
        self._llm_client = llm_client
        self._shared_context = shared_context or SharedContextManager()
        self._agents: Dict[str, SubAgent] = {}
        self._loader = SubAgentLoader(project_root)
        self._initialized = False

    async def initialize(self) -> None:
        """初始化所有 SubAgents"""
        if self._initialized:
            return

        # 扫描并加载所有 Agents
        self._agents = self._loader.scan_and_load(self._llm_client)

        if not self._agents:
            logger.info("未发现任何 SubAgent")
        else:
            logger.info(f"SubAgent 编排器初始化完成: {len(self._agents)} 个 Agent 已加载")

        self._initialized = True

    async def route(
        self,
        input_data: SubAgentInput,
        session_id: str = ""
    ) -> SubAgentOutput:
        """
        路由到最合适的 Agent

        流程：
        1. 评估每个 Agent 的 can_handle() 分数
        2. 选择分数最高的 Agent
        3. 执行并返回结果
        4. 更新共享上下文

        Args:
            input_data: 输入数据
            session_id: 会话 ID（用于上下文共享）

        Returns:
            SubAgentOutput: 输出结果
        """
        if not self._agents:
            return SubAgentOutput(
                success=False,
                response="没有可用的 Agent",
                error="未配置任何 SubAgent",
                source_type="subagent"
            )

        best_agent = None
        best_score = 0.0

        # 找到最合适的 Agent
        for agent_id, agent in self._agents.items():
            try:
                score = agent.can_handle(input_data)
                if score > best_score:
                    best_score = score
                    best_agent = agent
            except Exception as e:
                logger.warning(f"评估 Agent {agent_id} 失败: {e}")

        # 置信度阈值
        if best_score < 0.3:
            return SubAgentOutput(
                success=False,
                response="没有合适的 Agent 可以处理此任务",
                error=f"最佳匹配分数: {best_score:.2f}",
                source_type="subagent"
            )

        # 获取共享上下文
        if session_id:
            context = self._shared_context.get_context(session_id)
            input_data.context.update(context.to_dict()["state"])

        # 执行
        try:
            output = await best_agent.process(input_data)
            output.source_type = "subagent"
            output.agent_id = best_agent.agent_id

            # 更新共享上下文
            if session_id and output.success:
                context = self._shared_context.get_context(session_id)
                context.update(output.data)

            return output

        except Exception as e:
            logger.error(f"Agent {best_agent.agent_id} 执行失败: {e}")
            return SubAgentOutput(
                success=False,
                response="Agent 执行失败",
                error=str(e),
                source_type="subagent"
            )

    async def route_parallel(
        self,
        input_data: SubAgentInput,
        max_agents: int = 3,
        session_id: str = ""
    ) -> List[SubAgentOutput]:
        """
        并行路由到多个 Agents

        用于需要多个角度分析的场景

        Args:
            input_data: 输入数据
            max_agents: 最大并行 Agent 数量
            session_id: 会话 ID

        Returns:
            List[SubAgentOutput]: 输出结果列表
        """
        if not self._agents:
            return []

        # 评估所有 Agent
        scores = []
        for agent_id, agent in self._agents.items():
            try:
                score = agent.can_handle(input_data)
                scores.append((score, agent))
            except Exception as e:
                logger.warning(f"评估 Agent {agent_id} 失败: {e}")

        # 选择前 N 个
        scores.sort(key=lambda x: x[0], reverse=True)
        top_agents = [agent for score, agent in scores[:max_agents]]

        # 并行执行
        tasks = [agent.process(input_data) for agent in top_agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        outputs = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                outputs.append(SubAgentOutput(
                    success=False,
                    response="Agent 执行异常",
                    error=str(result),
                    agent_id=top_agents[i].agent_id,
                    source_type="subagent"
                ))
            else:
                result.source_type = "subagent"
                result.agent_id = top_agents[i].agent_id
                outputs.append(result)

        return outputs

    async def chain(
        self,
        input_data: SubAgentInput,
        chain_config: List[str],
        session_id: str = ""
    ) -> SubAgentOutput:
        """
        链式调用多个 Agents

        chain_config: ["agent1", "agent2", "agent3"]
        前一个 Agent 的输出作为下一个 Agent 的输入

        Args:
            input_data: 输入数据
            chain_config: Agent 链配置
            session_id: 会话 ID

        Returns:
            SubAgentOutput: 最终输出结果
        """
        current_input = input_data
        chain_info = []

        for agent_name in chain_config:
            if agent_name not in self._agents:
                return SubAgentOutput(
                    success=False,
                    error=f"Agent '{agent_name}' not found",
                    source_type="subagent",
                    chain_info=chain_info
                )

            agent = self._agents[agent_name]

            # 获取共享上下文
            if session_id:
                context = self._shared_context.get_context(session_id)
                current_input.context.update(context.to_dict()["state"])

            output = await agent.process(current_input)

            if not output.success:
                output.chain_info = chain_info
                return output

            chain_info.append(agent_name)

            # 将当前输出作为下一个的输入
            current_input = SubAgentInput(
                query=output.response,
                context={**current_input.context, **output.data},
                session_id=current_input.session_id
            )

            # 更新共享上下文
            if session_id:
                context = self._shared_context.get_context(session_id)
                context.update(output.data)

        output.chain_info = chain_info
        output.source_type = "subagent"
        return output

    async def route_stream(
        self,
        input_data: SubAgentInput,
        session_id: str = ""
    ) -> AsyncGenerator[str, None]:
        """
        流式路由到最合适的 Agent

        Args:
            input_data: 输入数据
            session_id: 会话 ID

        Yields:
            str: 响应片段
        """
        if not self._agents:
            yield "没有可用的 Agent"
            return

        best_agent = None
        best_score = 0.0

        for agent_id, agent in self._agents.items():
            try:
                score = agent.can_handle(input_data)
                if score > best_score:
                    best_score = score
                    best_agent = agent
            except Exception as e:
                logger.warning(f"评估 Agent {agent_id} 失败: {e}")

        if best_score < 0.3 or not best_agent:
            yield "没有合适的 Agent 可以处理此任务"
            return

        # 获取共享上下文
        if session_id:
            context = self._shared_context.get_context(session_id)
            input_data.context.update(context.to_dict()["state"])

        async for chunk in best_agent.process_stream(input_data):
            yield chunk

    def list_agents(self) -> List[str]:
        """列出所有已加载的 Agent"""
        return list(self._agents.keys())

    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取 Agent 信息"""
        if agent_id not in self._agents:
            return None

        agent = self._agents[agent_id]
        return {
            "id": agent.agent_id,
            "description": agent.config.description,
            "can_stream": agent.config.can_stream,
            "can_delegate": agent.config.can_delegate
        }

    def get_shared_context(self, session_id: str) -> AgentContext:
        """
        获取共享上下文

        Args:
            session_id: 会话 ID

        Returns:
            AgentContext: 上下文对象
        """
        return self._shared_context.get_context(session_id)

    async def shutdown(self) -> None:
        """关闭编排器"""
        self._agents.clear()
        self._shared_context.clear_all()
        self._initialized = False
        logger.info("SubAgent 编排器已关闭")
