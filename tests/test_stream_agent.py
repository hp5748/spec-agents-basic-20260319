"""
StreamAgent 集成测试

测试重构后的 StreamAgent 的 Function Calling 功能。
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.agent.stream_agent import StreamAgent
from src.llm_client import LLMClient, LLMConfig, LLMResponse, ToolCall
from src.agent.tool_registry import ToolRegistry
from src.adapters.core.factory import AdapterFactory
from src.adapters.core.types import ToolRequest, ToolResponse, AdapterType, AdapterConfig


@pytest.fixture
def mock_llm_client():
    """Mock LLM 客户端"""
    client = MagicMock(spec=LLMClient)
    return client


@pytest.fixture
def mock_memory():
    """Mock 记忆管理器"""
    memory = MagicMock()
    memory.get_messages = AsyncMock(return_value=[])
    memory.add_message = AsyncMock()
    memory.check_and_summarize = AsyncMock(return_value=None)
    return memory


@pytest.fixture
def mock_tool_registry():
    """Mock 工具注册表"""
    registry = MagicMock(spec=ToolRegistry)
    registry.to_openapi_schema = MagicMock(return_value=[
        {
            "type": "function",
            "function": {
                "name": "test_tool",
                "description": "测试工具",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer"},
                        "y": {"type": "integer"},
                    },
                },
            },
        }
    ])
    return registry


@pytest.fixture
def mock_adapter_factory():
    """Mock 适配器工厂"""
    factory = MagicMock(spec=AdapterFactory)
    factory.initialize = AsyncMock()
    factory.route = AsyncMock(
        return_value=ToolResponse(
            tool_name="test_tool",
            success=True,
            data={"result": 30},
        )
    )
    return factory


@pytest.fixture
async def agent(mock_llm_client, mock_memory, mock_tool_registry, mock_adapter_factory):
    """创建 StreamAgent 实例"""
    agent = StreamAgent(
        session_id="test_session",
        llm_client=mock_llm_client,
        memory=mock_memory,
        tool_registry=mock_tool_registry,
        adapter_factory=mock_adapter_factory,
    )
    await agent.initialize()
    yield agent


class TestStreamAgent:
    """StreamAgent 测试"""

    @pytest.mark.asyncio
    async def test_initialize(self, agent):
        """测试初始化"""
        assert agent._initialized is True

    @pytest.mark.asyncio
    async def test_chat_without_tools(self, agent, mock_llm_client):
        """测试无工具调用的对话"""
        # Mock LLM 响应（无 tool_calls）
        mock_llm_client.chat = AsyncMock(
            return_value=LLMResponse(content="你好！", tool_calls=None)
        )

        response = await agent.chat("你好")

        assert response == "你好！"
        assert "[LLM: DeepSeek-V3]" in response

    @pytest.mark.asyncio
    async def test_chat_with_tools(self, agent, mock_llm_client, mock_adapter_factory):
        """测试带工具调用的对话"""
        # 第一次调用：返回 tool_calls
        mock_llm_client.chat = AsyncMock(
            side_effect=[
                # 第一次：LLM 决定调用工具
                LLMResponse(
                    content=None,
                    tool_calls=[
                        ToolCall(
                            id="call_1",
                            function_name="test_tool",
                            arguments='{"x": 10, "y": 20}',
                        )
                    ],
                ),
                # 第二次：LLM 总结工具结果
                LLMResponse(content="计算结果是 30", tool_calls=None),
            ]
        )

        response = await agent.chat("计算 10 + 20")

        # 验证适配器被调用
        mock_adapter_factory.route.assert_called_once()
        call_args = mock_adapter_factory.route.call_args
        assert call_args[1]["tool_name"] == "test_tool"
        assert call_args[1]["parameters"] == {"x": 10, "y": 20}

        assert "计算结果是 30" in response

    @pytest.mark.asyncio
    async def test_chat_stream_without_tools(self, agent, mock_llm_client):
        """测试流式对话（无工具）"""
        mock_llm_client.chat = AsyncMock(
            return_value=LLMResponse(content="你好！", tool_calls=None)
        )

        chunks = []
        async for chunk in agent.chat_stream("你好"):
            chunks.append(chunk)

        full_response = "".join(chunks)
        assert "你好！" in full_response

    @pytest.mark.asyncio
    async def test_get_available_tools(self, agent):
        """测试获取可用工具"""
        tools = await agent.get_available_tools()

        assert len(tools) > 0
        assert tools[0]["type"] == "function"

    @pytest.mark.asyncio
    async def test_clear_history(self, agent, mock_memory):
        """测试清除历史"""
        await agent.clear_history()

        mock_memory.clear_session.assert_called_once_with("test_session")


class TestFunctionCallingFlow:
    """Function Calling 流程测试"""

    @pytest.mark.asyncio
    async def test_tool_call_execution(
        self, mock_llm_client, mock_memory, mock_tool_registry, mock_adapter_factory
    ):
        """测试工具调用执行流程"""
        agent = StreamAgent(
            session_id="test",
            llm_client=mock_llm_client,
            memory=mock_memory,
            tool_registry=mock_tool_registry,
            adapter_factory=mock_adapter_factory,
        )
        await agent.initialize()

        # 设置 LLM 响应
        mock_llm_client.chat = AsyncMock(
            side_effect=[
                LLMResponse(
                    content=None,
                    tool_calls=[
                        ToolCall(
                            id="call_1",
                            function_name="test_tool",
                            arguments='{"x": 5, "y": 3}',
                        )
                    ],
                ),
                LLMResponse(content="执行成功", tool_calls=None),
            ]
        )

        response = await agent.chat("执行工具")

        # 验证调用链
        assert agent._chain_tracker._calls[0]["source_name"] == "test_tool"

    @pytest.mark.asyncio
    async def test_tool_call_error_handling(
        self, mock_llm_client, mock_memory, mock_tool_registry, mock_adapter_factory
    ):
        """测试工具调用错误处理"""
        # Mock 工具调用失败
        mock_adapter_factory.route = AsyncMock(
            return_value=ToolResponse(
                tool_name="test_tool",
                success=False,
                error="工具执行失败",
            )
        )

        agent = StreamAgent(
            session_id="test",
            llm_client=mock_llm_client,
            memory=mock_memory,
            tool_registry=mock_tool_registry,
            adapter_factory=mock_adapter_factory,
        )
        await agent.initialize()

        mock_llm_client.chat = AsyncMock(
            side_effect=[
                LLMResponse(
                    content=None,
                    tool_calls=[
                        ToolCall(
                            id="call_1",
                            function_name="test_tool",
                            arguments='{}',
                        )
                    ],
                ),
                LLMResponse(content="抱歉，工具调用失败了", tool_calls=None),
            ]
        )

        response = await agent.chat("执行工具")

        # 验证 LLM 仍然能够处理错误
        assert "抱歉" in response or "失败" in response


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
