"""
聊天路由

提供流式对话 API。
"""

import json
import logging
import logging
from typing import Optional, AsyncGenerator

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..dependencies import get_llm_client, get_session_id, get_stream_agent
from ...llm_client import LLMClient
from ...memory import ConversationMemory, get_memory_manager
from ...agent.stream_agent import StreamAgent
from ...agent.tool_registry import get_global_registry


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    session_id: Optional[str] = None
    stream: bool = True


class ChatMessage(BaseModel):
    """聊天消息"""
    role: str
    content: str


async def generate_sse_stream(
    agent: StreamAgent,
    session_id: str,
    user_message: str
) -> AsyncGenerator[str, None]:
    """
    生成 SSE 流式响应（使用 StreamAgent，支持 Skills）

    格式：
    data: {"type": "content", "content": "文本块"}\n\n
    data: {"type": "done", "session_id": "xxx"}\n\n
    """
    try:
        # 发送开始事件
        yield f'data: {json.dumps({"type": "start", "session_id": session_id}, ensure_ascii=False)}\n\n'

        full_response = ""

        # 流式调用 StreamAgent（自动处理 Skills 匹配）
        async for chunk in agent.chat_stream(user_message):
            full_response += chunk
            yield f'data: {json.dumps({"type": "content", "content": chunk}, ensure_ascii=False)}\n\n'

        # 发送完成事件
        yield f'data: {json.dumps({"type": "done", "session_id": session_id}, ensure_ascii=False)}\n\n'

    except Exception as e:
        logger.error(f"流式响应错误: {e}")
        yield f'data: {json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)}\n\n'


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    llm_client: LLMClient = Depends(get_llm_client)
):
    """
    流式聊天接口

    使用 StreamAgent 处理请求，支持 Skills 调用。
    """
    session_id = get_session_id(request.session_id)
    agent = get_stream_agent(session_id)

    # 返回 SSE 流
    return StreamingResponse(
        generate_sse_stream(
            agent=agent,
            session_id=session_id,
            user_message=request.message
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/message")
async def chat_message(
    request: ChatRequest,
    llm_client: LLMClient = Depends(get_llm_client)
):
    """
    非流式聊天接口

    使用 StreamAgent 处理请求，支持 Skills 调用。
    """
    session_id = get_session_id(request.session_id)
    agent = get_stream_agent(session_id)

    # 调用 StreamAgent
    response = await agent.chat(request.message)

    return {
        "session_id": session_id,
        "response": response
    }


@router.get("/tools")
async def list_tools():
    """列出所有可用工具"""
    registry = get_global_registry()
    tools = registry.list_tool_names()
    schema = registry.to_openapi_schema()

    return {
        "tools": tools,
        "count": len(tools),
        "schema": schema
    }
