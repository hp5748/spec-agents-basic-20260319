"""
对话总结器

负责将长对话压缩成简洁的摘要。
"""

import logging
from typing import List, Dict, Optional

from ..llm_client import LLMClient, LLMConfig


logger = logging.getLogger(__name__)

# 总结提示词模板
SUMMARY_PROMPT = """你是一个对话总结助手。请将以下对话历史压缩成一个简洁的摘要。

要求：
1. 保留关键信息和重要细节
2. 如果有已有摘要，请在此基础上更新
3. 摘要应该能帮助 AI 理解之前的对话上下文
4. 控制在 200-300 字以内

{existing_summary_section}

对话历史：
{conversation}

请生成摘要："""


class ConversationSummarizer:
    """
    对话总结器

    使用 LLM 生成对话摘要。
    """

    def __init__(self):
        """初始化总结器"""
        self._llm_client: Optional[LLMClient] = None
        self._initialized = False

    async def initialize(self) -> bool:
        """初始化 LLM 客户端"""
        if self._initialized:
            return True

        try:
            config = LLMConfig.from_env()
            self._llm_client = LLMClient(config)
            self._initialized = True
            logger.info("对话总结器初始化完成")
            return True
        except Exception as e:
            logger.error(f"对话总结器初始化失败: {e}")
            return False

    async def summarize(
        self,
        messages: List[Dict],
        existing_summary: Optional[str] = None
    ) -> Optional[str]:
        """
        生成对话摘要

        Args:
            messages: 对话消息列表
            existing_summary: 已有的摘要（用于增量更新）

        Returns:
            生成的摘要
        """
        if not self._initialized or not self._llm_client:
            logger.warning("总结器未初始化")
            return None

        if len(messages) < 2:
            return None

        try:
            # 构建对话文本
            conversation = self._format_conversation(messages)

            # 构建已有摘要部分
            existing_section = ""
            if existing_summary:
                existing_section = f"已有摘要：\n{existing_summary}\n"

            # 构建提示词
            prompt = SUMMARY_PROMPT.format(
                existing_summary_section=existing_section,
                conversation=conversation
            )

            # 调用 LLM
            summary = await self._llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3
            )

            logger.debug(f"生成摘要: {summary[:100]}...")
            return summary.strip()

        except Exception as e:
            logger.error(f"生成摘要失败: {e}")
            return None

    def _format_conversation(self, messages: List[Dict]) -> str:
        """格式化对话为文本"""
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            role_name = {"user": "用户", "assistant": "助手", "system": "系统"}.get(role, role)
            lines.append(f"[{role_name}]: {content}")
        return "\n".join(lines)
