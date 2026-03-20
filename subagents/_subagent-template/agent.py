"""
SubAgent 模板

复制此目录并重命名，然后实现你自己的 Agent。
"""

from src.subagent import SubAgent, SubAgentInput, SubAgentOutput, AgentConfig


class Agent(SubAgent):
    """
    我的 Agent

    在 AGENT.md 中添加详细描述。
    """

    def __init__(self, agent_id: str, config: AgentConfig, llm_client=None):
        super().__init__(agent_id, config, llm_client)

        # 设置系统提示词（可选）
        self.set_system_prompt("你是一个专业的 AI Agent，负责处理特定任务。")

    async def process(self, input_data: SubAgentInput) -> SubAgentOutput:
        """
        处理输入并返回输出

        这是 Agent 的核心方法，实现你的业务逻辑。
        """
        try:
            # 实现你的逻辑
            result = await self._do_something(input_data.query)

            return SubAgentOutput(
                success=True,
                response=f"处理完成: {result}",
                data={"input": input_data.query}
            )
        except Exception as e:
            return SubAgentOutput(
                success=False,
                response="",
                error=str(e)
            )

    def can_handle(self, input_data: SubAgentInput) -> float:
        """
        判断是否能处理此输入

        返回置信度 0.0-1.0

        方法1: 关键词匹配
        方法2: LLM 判断（如果有 llm_client）
        """
        # 方法1: 关键词匹配
        keywords = ["处理", "执行", "你的", "关键词"]
        for kw in keywords:
            if kw in input_data.query:
                return 0.8

        # 方法2: LLM 判断（如果有 llm_client）
        # if self._llm_client:
        #     # 使用 LLM 判断...
        #     pass

        return 0.0

    async def _do_something(self, query: str) -> str:
        """实际处理逻辑"""
        # 在这里实现你的业务逻辑
        return f"已处理: {query}"
