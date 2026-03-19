"""
对话记忆管理

负责 Session 和 Message 的管理，以及对话历史存储。
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from .summarizer import ConversationSummarizer


logger = logging.getLogger(__name__)

# 配置参数
SUMMARY_THRESHOLD = 20  # 触发总结的消息数
KEEP_RECENT = 10        # 总结后保留的最近消息数


@dataclass
class Session:
    """会话数据"""
    session_id: str
    messages: List[Dict] = field(default_factory=list)
    summary: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class ConversationMemory:
    """
    对话记忆管理器

    功能：
    - 管理多个 Session
    - 存储对话历史
    - 触发对话总结
    - 内存存储（可选持久化）
    """

    def __init__(
        self,
        summary_threshold: int = SUMMARY_THRESHOLD,
        keep_recent: int = KEEP_RECENT
    ):
        """
        初始化记忆管理器

        Args:
            summary_threshold: 触发总结的消息数阈值
            keep_recent: 总结后保留的最近消息数
        """
        self._sessions: Dict[str, Session] = {}
        self._summary_threshold = summary_threshold
        self._keep_recent = keep_recent
        self._summarizer = ConversationSummarizer()
        self._initialized = False

    async def initialize(self) -> bool:
        """初始化记忆管理器"""
        if self._initialized:
            return True

        try:
            await self._summarizer.initialize()
            self._initialized = True
            logger.info(f"记忆管理器初始化完成 (threshold={self._summary_threshold}, keep={self._keep_recent})")
            return True
        except Exception as e:
            logger.error(f"记忆管理器初始化失败: {e}")
            return False

    async def cleanup(self) -> None:
        """清理资源"""
        self._sessions.clear()
        self._initialized = False
        logger.info("记忆管理器已清理")

    def _get_or_create_session(self, session_id: str) -> Session:
        """获取或创建 Session"""
        if session_id not in self._sessions:
            self._sessions[session_id] = Session(session_id=session_id)
        return self._sessions[session_id]

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str
    ) -> None:
        """
        添加消息到会话

        Args:
            session_id: 会话 ID
            role: 角色 (user/assistant)
            content: 消息内容
        """
        session = self._get_or_create_session(session_id)

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }

        session.messages.append(message)
        session.updated_at = datetime.now().isoformat()

        logger.debug(f"Session {session_id}: 添加消息 [{role}], 总数: {len(session.messages)}")

    async def get_messages(
        self,
        session_id: str,
        include_summary: bool = True
    ) -> List[Dict]:
        """
        获取会话消息

        Args:
            session_id: 会话 ID
            include_summary: 是否包含摘要

        Returns:
            消息列表
        """
        session = self._get_or_create_session(session_id)

        messages = []

        # 如果有摘要，添加到消息开头
        if include_summary and session.summary:
            messages.append({
                "role": "system",
                "content": f"[对话摘要]\n{session.summary}"
            })

        # 添加所有消息
        messages.extend(session.messages)

        return messages

    async def get_message_count(self, session_id: str) -> int:
        """获取消息数量"""
        session = self._sessions.get(session_id)
        return len(session.messages) if session else 0

    async def has_summary(self, session_id: str) -> bool:
        """检查是否有摘要"""
        session = self._sessions.get(session_id)
        return session is not None and session.summary is not None

    async def get_summary(self, session_id: str) -> Optional[str]:
        """获取摘要"""
        session = self._sessions.get(session_id)
        return session.summary if session else None

    async def check_and_summarize(self, session_id: str) -> Optional[str]:
        """
        检查并触发总结

        当消息数超过阈值时自动触发总结。

        Returns:
            摘要内容，如果未触发总结则返回 None
        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        if len(session.messages) < self._summary_threshold:
            return None

        return await self.force_summarize(session_id)

    async def force_summarize(self, session_id: str) -> Optional[str]:
        """
        强制触发总结

        对当前会话进行总结，并保留最近的 N 条消息。

        Returns:
            摘要内容
        """
        session = self._sessions.get(session_id)
        if not session or len(session.messages) < 2:
            return None

        try:
            # 生成摘要
            summary = await self._summarizer.summarize(
                messages=session.messages,
                existing_summary=session.summary
            )

            if summary:
                # 更新摘要
                session.summary = summary

                # 保留最近的消息
                if len(session.messages) > self._keep_recent:
                    removed_count = len(session.messages) - self._keep_recent
                    session.messages = session.messages[-self._keep_recent:]
                    logger.info(
                        f"Session {session_id}: 总结完成，"
                        f"压缩 {removed_count} 条消息，保留 {self._keep_recent} 条"
                    )

                return summary

        except Exception as e:
            logger.error(f"生成摘要失败: {e}")

        return None

    async def clear_session(self, session_id: str) -> None:
        """清除会话"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Session {session_id}: 已清除")

    async def list_sessions(self) -> List[str]:
        """列出所有会话 ID"""
        return list(self._sessions.keys())


# 全局记忆管理器实例
_memory_manager: Optional[ConversationMemory] = None


def get_memory_manager() -> ConversationMemory:
    """获取全局记忆管理器实例"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = ConversationMemory()
    return _memory_manager
