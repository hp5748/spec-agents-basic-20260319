"""
SubAgent 编排器

负责：
- 管理 SubAgent 生命周期
- 路由任务到合适的 Agent
- 协调多个 Agent 并行执行
- 聚合 Agent 返回结果
"""

import asyncio
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from .config import SubAgentLoader
from .base_agent import SubAgent, SubAgentInput, SubAgentOutput


logger = logging.getLogger(__name__)


class SubAgentOrchestrator:
    """
    SubAgent 编排器

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

    def __init__(self, project_root: str = ".", llm_client: Optional[Any] = None):
        self._project_root = project_root
        self._llm_client = llm_client
        self._agents: Dict[str, SubAgent] = {}
        self._loader = SubAgentLoader(project_root)

    async def initialize(self) -> None:
        """初始化所有 SubAgents"""
        # 扫描并加载所有 Agents
        self._agents = self._loader.scan_and_load(self._llm_client)

        if not self._agents:
            logger.info("未发现任何 SubAgent")
            return

        logger.info(f"SubAgent 编排器初始化完成: {len(self._agents)} 个 Agent 已加载")

    async def route(
        self,
        input_data: SubAgentInput
    ) -> SubAgentOutput:
        """
        路由到最合适的 Agent

        流程：
        1. 评估每个 Agent 的 can_handle() 分数
        2. 选择分数最高的 Agent
        3. 执行并返回结果
        """
        if not self._agents:
            return SubAgentOutput(
                success=False,
                response="没有可用的 Agent",
                error="未配置任何 SubAgent"
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
                error=f"最佳匹配分数: {best_score:.2f}"
            )

        # 执行
        try:
            return await best_agent.process(input_data)
        except Exception as e:
            logger.error(f"Agent {best_agent.agent_id} 执行失败: {e}")
            return SubAgentOutput(
                success=False,
                response="Agent 执行失败",
                error=str(e)
            )

    async def route_parallel(
        self,
        input_data: SubAgentInput,
        max_agents: int = 3
    ) -> List[SubAgentOutput]:
        """
        并行路由到多个 Agents

        用于需要多个角度分析的场景
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
                    agent_id=top_agents[i].agent_id
                ))
            else:
                outputs.append(result)

        return outputs

    async def chain(
        self,
        input_data: SubAgentInput,
        chain_config: List[str]
    ) -> SubAgentOutput:
        """
        链式调用多个 Agents

        chain_config: ["agent1", "agent2", "agent3"]
        前一个 Agent 的输出作为下一个 Agent 的输入
        """
        current_input = input_data
        final_output = None

        for agent_name in chain_config:
            if agent_name not in self._agents:
                return SubAgentOutput(
                    success=False,
                    error=f"Agent '{agent_name}' not found"
                )

            agent = self._agents[agent_name]
            output = await agent.process(current_input)

            if not output.success:
                return output

            # 将当前输出作为下一个的输入
            current_input = SubAgentInput(
                query=output.response,
                context={**current_input.context, **output.data},
                session_id=current_input.session_id
            )

            final_output = output

        return final_output

    async def route_stream(
        self,
        input_data: SubAgentInput
    ) -> AsyncGenerator[str, None]:
        """
        流式路由到最合适的 Agent
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

    async def shutdown(self) -> None:
        """关闭编排器"""
        self._agents.clear()
        logger.info("SubAgent 编排器已关闭")
