"""
会话路由

提供会话历史管理 API。
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel

from ..dependencies import get_session_id
from ...memory import get_memory_manager


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/session", tags=["session"])


class Message(BaseModel):
    """消息模型"""
    role: str
    content: str


class SessionHistory(BaseModel):
    """会话历史"""
    session_id: str
    messages: List[Message]
    message_count: int
    has_summary: bool


class SessionSummary(BaseModel):
    """会话摘要"""
    session_id: str
    summary: str
    original_count: int


@router.get("/{session_id}", response_model=SessionHistory)
async def get_session(session_id: str):
    """
    获取会话历史

    返回指定会话的所有消息。
    """
    memory_manager = get_memory_manager()

    messages = await memory_manager.get_messages(session_id)
    has_summary = await memory_manager.has_summary(session_id)

    return SessionHistory(
        session_id=session_id,
        messages=[Message(**msg) for msg in messages],
        message_count=len(messages),
        has_summary=has_summary
    )


@router.delete("/{session_id}")
async def clear_session(session_id: str):
    """
    清除会话历史

    删除指定会话的所有消息。
    """
    memory_manager = get_memory_manager()

    await memory_manager.clear_session(session_id)

    return {"status": "ok", "message": f"Session {session_id} cleared"}


@router.post("/{session_id}/summarize", response_model=SessionSummary)
async def summarize_session(session_id: str):
    """
    手动触发会话总结

    对当前会话进行总结并压缩历史。
    """
    memory_manager = get_memory_manager()

    summary = await memory_manager.force_summarize(session_id)

    if summary is None:
        raise HTTPException(
            status_code=400,
            detail="No messages to summarize"
        )

    return SessionSummary(
        session_id=session_id,
        summary=summary,
        original_count=await memory_manager.get_message_count(session_id)
    )


@router.get("/{session_id}/summary")
async def get_summary(session_id: str):
    """
    获取会话摘要

    返回当前会话的摘要内容。
    """
    memory_manager = get_memory_manager()

    summary = await memory_manager.get_summary(session_id)

    if summary is None:
        raise HTTPException(
            status_code=404,
            detail="No summary available"
        )

    return {
        "session_id": session_id,
        "summary": summary
    }
