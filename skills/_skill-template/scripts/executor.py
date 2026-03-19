"""
Skill 执行器模板

所有 Skill 的 scripts/executor.py 应遵循此模板。
"""

from typing import Any, Dict
from dataclasses import dataclass, field


@dataclass
class SkillResult:
    """执行结果"""
    success: bool
    response: str
    data: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    used_tools: list = field(default_factory=list)


@dataclass
class SkillContext:
    """执行上下文"""
    session_id: str
    user_input: str
    intent: str
    chat_history: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class SkillExecutor:
    """
    Skill 执行器

    必须实现 execute 方法。
    """

    def __init__(self):
        """初始化执行器"""
        self.name = "skill-template"

    async def execute(self, context: SkillContext) -> SkillResult:
        """
        执行 Skill

        Args:
            context: 执行上下文

        Returns:
            SkillResult: 执行结果
        """
        try:
            # 1. 解析输入
            user_input = context.user_input

            # 2. 执行业务逻辑
            result_data = self._process(user_input, context)

            # 3. 生成响应
            response = self._format_response(result_data)

            return SkillResult(
                success=True,
                response=response,
                data=result_data
            )

        except Exception as e:
            return SkillResult(
                success=False,
                response="",
                error=str(e)
            )

    def _process(self, user_input: str, context: SkillContext) -> Dict[str, Any]:
        """
        处理业务逻辑

        Args:
            user_input: 用户输入
            context: 执行上下文

        Returns:
            Dict: 处理结果
        """
        # 在这里实现具体业务逻辑
        return {
            "input": user_input,
            "processed": True
        }

    def _format_response(self, data: Dict[str, Any]) -> str:
        """
        格式化响应

        Args:
            data: 结果数据

        Returns:
            str: 格式化后的响应
        """
        # 在这里实现响应格式化
        return f"处理完成: {data}"


# 同步执行入口（可选）
def execute_sync(context: SkillContext) -> SkillResult:
    """同步执行入口"""
    import asyncio
    executor = SkillExecutor()
    return asyncio.run(executor.execute(context))
