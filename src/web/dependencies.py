"""
依赖注入

提供 FastAPI 依赖注入组件。
"""

from typing import Optional
from functools import lru_cache

from ..llm_client import LLMClient, LLMConfig
from ..agent.stream_agent import StreamAgent


@lru_cache()
def get_llm_client() -> LLMClient:
    """获取 LLM 客户端（单例）"""
    config = LLMConfig.from_env()
    return LLMClient(config)


# StreamAgent 缓存（按 session_id）
_agent_cache: dict = {}


def get_stream_agent(session_id: str) -> StreamAgent:
    """获取 StreamAgent（按会话缓存）"""
    if session_id not in _agent_cache:
        _agent_cache[session_id] = StreamAgent(session_id)
    return _agent_cache[session_id]


def get_session_id(session_id: Optional[str] = None) -> str:
    """获取或创建会话 ID"""
    if session_id:
        return session_id
    import uuid
    return str(uuid.uuid4())
