"""
流式 Agent

封装 LLM 客户端，提供流式对话能力。
支持 Skill 调用（通过意图识别）。
"""

import logging
from typing import AsyncGenerator, List, Dict, Optional

from ..llm_client import LLMClient, LLMConfig
from ..memory import ConversationMemory, get_memory_manager
from ..intent import IntentRecognizer, IntentResult
from ..skill_executor import SkillExecutor, SkillContext, SkillResult


logger = logging.getLogger(__name__)


class StreamAgent:
    """
    流式 Agent

    功能：
    - 意图识别 → Skill 匹配 → Skill 执行
    - 无匹配时降级到 LLM 直接响应
    - 集成记忆管理器
    """

    def __init__(
        self,
        session_id: str,
        llm_client: Optional[LLMClient] = None,
        memory: Optional[ConversationMemory] = None,
        skills_dir: str = "skills"
    ):
        """
        初始化流式 Agent

        Args:
            session_id: 会话 ID
            llm_client: LLM 客户端（可选）
            memory: 记忆管理器（可选）
            skills_dir: Skill 目录
        """
        self.session_id = session_id
        self._llm_client = llm_client or self._create_llm_client()
        self._memory = memory or get_memory_manager()
        self._skills_dir = skills_dir

        # Skill 相关（延迟初始化）
        self._intent_recognizer: Optional[IntentRecognizer] = None
        self._skill_executor: Optional[SkillExecutor] = None
        self._skills_initialized = False

    def _create_llm_client(self) -> LLMClient:
        """创建 LLM 客户端"""
        config = LLMConfig.from_env()
        return LLMClient(config)

    def _init_skills(self) -> None:
        """延迟初始化 Skill 相关组件"""
        if self._skills_initialized:
            return

        try:
            self._intent_recognizer = IntentRecognizer(self._skills_dir)
            self._skill_executor = SkillExecutor(self._skills_dir)
            self._skills_initialized = True
            logger.info(f"Session {self.session_id}: Skill 系统已初始化")
        except Exception as e:
            logger.warning(f"Skill 系统初始化失败: {e}")
            self._skills_initialized = False

    async def chat_stream(
        self,
        user_input: str,
        include_history: bool = True
    ) -> AsyncGenerator[str, None]:
        """
        流式对话

        流程：
        1. 意图识别
        2. Skill 匹配
        3. 有匹配 → 执行 Skill → 返回结果
        4. 无匹配 → 调用 LLM → 返回结果

        Args:
            user_input: 用户输入
            include_history: 是否包含对话历史

        Yields:
            str: 响应文本片段
        """
        # 初始化 Skill 系统
        self._init_skills()

        # 尝试 Skill 匹配
        skill_result = await self._try_skill(user_input)

        if skill_result and skill_result.success:
            # Skill 执行成功，直接返回结果
            full_response = ""
            for char in skill_result.response:
                full_response += char
                yield char

            # 保存到记忆
            await self._save_to_memory(user_input, full_response)
            return

        # Skill 未匹配或执行失败，走 LLM
        full_response = ""
        async for chunk in self._llm_chat_stream(user_input, include_history):
            full_response += chunk
            yield chunk

        # 保存到记忆
        await self._save_to_memory(user_input, full_response)

    async def _try_skill(self, user_input: str) -> Optional[SkillResult]:
        """
        尝试匹配并执行 Skill

        Args:
            user_input: 用户输入

        Returns:
            Optional[SkillResult]: Skill 执行结果，None 表示未匹配
        """
        if not self._intent_recognizer or not self._skill_executor:
            return None

        # 意图识别
        intent_result = self._intent_recognizer.recognize(user_input)

        if not intent_result.skill_name:
            logger.debug(f"未匹配到 Skill: {user_input[:50]}...")
            return None

        # 置信度检查
        if intent_result.confidence < 0.3:
            logger.info(
                f"Skill 置信度过低 ({intent_result.confidence:.2f}), "
                f"跳过: {intent_result.skill_name}"
            )
            return None

        logger.info(
            f"匹配到 Skill: {intent_result.skill_name} "
            f"(confidence={intent_result.confidence:.2f})"
        )

        # 构建 Skill 上下文
        context = SkillContext(
            session_id=self.session_id,
            user_input=user_input,
            intent=intent_result.matched_intents[0] if intent_result.matched_intents else "",
            metadata={
                "matched_keywords": intent_result.matched_keywords
            }
        )

        # 执行 Skill
        result = await self._skill_executor.execute(intent_result.skill_name, context)

        if result.success:
            logger.info(f"Skill 执行成功: {intent_result.skill_name}")
        else:
            logger.warning(f"Skill 执行失败: {result.error}")

        return result

    async def _llm_chat_stream(
        self,
        user_input: str,
        include_history: bool
    ) -> AsyncGenerator[str, None]:
        """
        调用 LLM 流式响应

        Args:
            user_input: 用户输入
            include_history: 是否包含历史

        Yields:
            str: 响应片段
        """
        messages = []

        if include_history:
            history = await self._memory.get_messages(self.session_id)
            for msg in history:
                if "role" in msg and "content" in msg:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })

        messages.append({
            "role": "user",
            "content": user_input
        })

        async for chunk in self._llm_client.chat_stream(messages):
            yield chunk

    async def _save_to_memory(self, user_input: str, response: str) -> None:
        """
        保存对话到记忆

        Args:
            user_input: 用户输入
            response: 助手响应
        """
        await self._memory.add_message(
            session_id=self.session_id,
            role="user",
            content=user_input
        )
        await self._memory.add_message(
            session_id=self.session_id,
            role="assistant",
            content=response
        )

        # 检查是否需要总结
        summary = await self._memory.check_and_summarize(self.session_id)
        if summary:
            logger.info(f"Session {self.session_id}: 对话已自动总结")

    async def chat(self, user_input: str, include_history: bool = True) -> str:
        """
        非流式对话

        Args:
            user_input: 用户输入
            include_history: 是否包含对话历史

        Returns:
            str: 完整响应
        """
        # 初始化 Skill 系统
        self._init_skills()

        # 尝试 Skill 匹配
        skill_result = await self._try_skill(user_input)

        if skill_result and skill_result.success:
            await self._save_to_memory(user_input, skill_result.response)
            return skill_result.response

        # 走 LLM
        messages = []

        if include_history:
            history = await self._memory.get_messages(self.session_id)
            for msg in history:
                if "role" in msg and "content" in msg:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })

        messages.append({
            "role": "user",
            "content": user_input
        })

        response = await self._llm_client.chat(messages)
        await self._save_to_memory(user_input, response)

        return response

    async def get_history(self) -> List[Dict]:
        """获取对话历史"""
        return await self._memory.get_messages(self.session_id)

    async def clear_history(self) -> None:
        """清除对话历史"""
        await self._memory.clear_session(self.session_id)
