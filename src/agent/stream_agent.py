"""
流式 Agent (Agentic 架构版本)

基于 Function Calling 的智能体，让 LLM 自主决策工具调用。
废弃 IntentRecognizer，全面拥抱 LLM 驱动。

核心流程：
  用户输入 → 构建 tools 参数 → LLM 决策
    ↓
  有 tool_calls → AdapterFactory 执行 → 收集结果 → 再次请求 LLM 总结
    ↓
  无 tool_calls → 直接返回 LLM 响应
"""

import asyncio
import json
import logging
from typing import AsyncGenerator, List, Dict, Optional, Any

from ..llm_client import LLMClient, LLMConfig, LLMResponse, ToolCall
from ..memory.conversation import ConversationMemory, get_memory_manager
from ..memory.shared_state import SharedState, ToolResult
from ..agent.tool_registry import ToolRegistry, get_global_registry
from ..adapters.core.factory import AdapterFactory, get_global_factory
from ..agent.chain_tracker import ChainTracker


logger = logging.getLogger(__name__)


class StreamAgent:
    """
    流式 Agent (Agentic 版本)

    功能：
    - LLM Function Calling 驱动决策
    - 统一工具注册表管理所有能力
    - 适配器工厂执行工具
    - 调用链追踪
    - 共享状态支持
    """

    def __init__(
        self,
        session_id: str,
        llm_client: Optional[LLMClient] = None,
        memory: Optional[ConversationMemory] = None,
        tool_registry: Optional[ToolRegistry] = None,
        adapter_factory: Optional[AdapterFactory] = None,
        project_root: str = ".",
    ):
        """
        初始化流式 Agent

        Args:
            session_id: 会话 ID
            llm_client: LLM 客户端（可选）
            memory: 记忆管理器（可选）
            tool_registry: 工具注册表（可选）
            adapter_factory: 适配器工厂（可选）
            project_root: 项目根目录
        """
        self.session_id = session_id
        self._project_root = project_root

        # 核心组件
        self._llm_client = llm_client or self._create_llm_client()
        self._memory = memory or get_memory_manager()
        self._tool_registry = tool_registry or get_global_registry()
        self._adapter_factory = adapter_factory or get_global_factory()

        # 共享状态
        self._shared_state = SharedState(session_id=self.session_id)

        # 调用链追踪
        self._chain_tracker = ChainTracker()

        # 初始化状态
        self._initialized = False

    def _create_llm_client(self) -> LLMClient:
        """创建 LLM 客户端"""
        config = LLMConfig.from_env()
        return LLMClient(config)

    async def initialize(self) -> None:
        """初始化 Agent"""
        if self._initialized:
            return

        logger.info(f"初始化 StreamAgent: {self.session_id}")

        # 适配器工厂无需异步初始化
        # 适配器会在首次使用时通过 create_adapter 创建

        self._initialized = True

    async def chat_stream(
        self,
        user_input: str,
        include_history: bool = True,
    ) -> AsyncGenerator[str, None]:
        """
        流式对话

        Agentic 流程：
        1. 构建 messages（包含历史）
        2. 从 ToolRegistry 获取所有工具的 schema
        3. 调用 LLM（带 tools 参数）
        4. 如果 LLM 返回 tool_calls：
           - 通过 AdapterFactory 执行工具
           - 收集结果
           - 再次请求 LLM 总结
        5. 流式输出最终响应

        Args:
            user_input: 用户输入
            include_history: 是否包含对话历史

        Yields:
            str: 响应文本片段
        """
        await self.initialize()

        # 1. 构建消息历史
        messages = await self._build_messages(user_input, include_history)

        # 2. 获取工具 schema（OpenAI API 期望数组格式）
        tools_schema = self._tool_registry.to_openapi_schema()
        tools = tools_schema.get("tools", []) if tools_schema else None

        # 3. 调用 LLM（带 Function Calling）
        response = await self._llm_client.chat(
            messages=messages,
            tools=tools,
        )

        # 4. 处理工具调用
        if response.has_tool_calls():
            # 执行工具并获取总结
            async for chunk in self._handle_tool_calls_stream(
                messages, response.tool_calls, tools
            ):
                yield chunk
        else:
            # 直接输出 LLM 响应
            if response.content:
                for char in response.content:
                    yield char

        # 5. 追加调用链签名
        signature = self._chain_tracker.format_signature()
        for char in signature:
            yield char

        # 6. 保存到记忆
        full_response = await self._collect_response(response.content or "")
        await self._save_to_memory(user_input, full_response)

        # 7. 清空调用链
        self._chain_tracker.clear()

    async def _handle_tool_calls_stream(
        self,
        messages: List[Dict[str, str]],
        tool_calls: List[ToolCall],
        tools: List[Dict[str, Any]],
    ) -> AsyncGenerator[str, None]:
        """
        处理工具调用（流式）

        Args:
            messages: 原始消息
            tool_calls: LLM 返回的工具调用
            tools: 工具 schema

        Yields:
            str: 响应文本片段
        """
        # 添加助手消息（包含 tool_calls）
        messages.append({
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function_name,
                        "arguments": tc.arguments,
                    },
                }
                for tc in tool_calls
            ],
        })

        # 执行所有工具调用
        tool_results = []
        for tool_call in tool_calls:
            try:
                # 解析参数
                arguments = json.loads(tool_call.arguments)

                # 通过工厂执行
                result = await self._adapter_factory.route(
                    tool_name=tool_call.function_name,
                    parameters=arguments,
                    session_id=self.session_id,
                )

                # 记录调用链
                self._chain_tracker.add(
                    source_type="tool",
                    source_name=tool_call.function_name,
                    confidence=1.0,  # LLM 调用，置信度最高
                )

                # 构建工具结果消息
                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps({
                        "success": result.success,
                        "data": result.data,
                        "error": result.error,
                    }),
                })

                # 更新共享状态
                await self._shared_state.add_tool_result(
                    ToolResult(
                        tool_name=tool_call.function_name,
                        success=result.success,
                        data=result.data if result.success else None,
                        error=result.error,
                    )
                )

            except Exception as e:
                logger.error(f"工具调用失败 {tool_call.function_name}: {e}")
                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps({
                        "success": False,
                        "error": str(e),
                    }),
                })

        # 添加工具结果到消息
        messages.extend(tool_results)

        # 再次请求 LLM 进行总结
        final_response = await self._llm_client.chat(
            messages=messages,
            tools=tools if tools else None,
        )

        # 流式输出总结
        if final_response.content:
            for char in final_response.content:
                yield char

    async def chat(
        self,
        user_input: str,
        include_history: bool = True,
    ) -> str:
        """
        非流式对话

        Args:
            user_input: 用户输入
            include_history: 是否包含对话历史

        Returns:
            str: 完整响应
        """
        await self.initialize()

        # 构建消息
        messages = await self._build_messages(user_input, include_history)

        # 获取工具 schema（OpenAI API 期望数组格式）
        tools_schema = self._tool_registry.to_openapi_schema()
        tools = tools_schema.get("tools", []) if tools_schema else None

        # 调用 LLM
        response = await self._llm_client.chat(
            messages=messages,
            tools=tools,
        )

        # 处理工具调用
        if response.has_tool_calls():
            result = await self._handle_tool_calls(
                messages, response.tool_calls, tools
            )
            full_response = result
        else:
            full_response = response.content or ""

        # 追加签名
        signature = self._chain_tracker.format_signature()
        full_response += signature

        # 保存
        await self._save_to_memory(user_input, full_response)

        # 清理
        self._chain_tracker.clear()

        return full_response

    async def _handle_tool_calls(
        self,
        messages: List[Dict[str, str]],
        tool_calls: List[ToolCall],
        tools: List[Dict[str, Any]],
    ) -> str:
        """处理工具调用（非流式）"""
        # 添加助手消息
        messages.append({
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function_name,
                        "arguments": tc.arguments,
                    },
                }
                for tc in tool_calls
            ],
        })

        # 执行工具
        tool_results = []
        for tool_call in tool_calls:
            try:
                arguments = json.loads(tool_call.arguments)
                result = await self._adapter_factory.route(
                    tool_name=tool_call.function_name,
                    parameters=arguments,
                    session_id=self.session_id,
                )

                self._chain_tracker.add(
                    source_type="tool",
                    source_name=tool_call.function_name,
                    confidence=1.0,
                )

                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps({
                        "success": result.success,
                        "data": result.data,
                        "error": result.error,
                    }),
                })

            except Exception as e:
                logger.error(f"工具调用失败 {tool_call.function_name}: {e}")
                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps({"success": False, "error": str(e)}),
                })

        messages.extend(tool_results)

        # 请求总结
        final_response = await self._llm_client.chat(
            messages=messages,
            tools=tools if tools else None,
        )

        return final_response.content or ""

    async def _build_messages(
        self,
        user_input: str,
        include_history: bool,
    ) -> List[Dict[str, str]]:
        """构建消息列表"""
        messages = []

        if include_history:
            history = await self._memory.get_messages(self.session_id)
            for msg in history:
                if "role" in msg and "content" in msg:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })

        messages.append({"role": "user", "content": user_input})
        return messages

    async def _save_to_memory(self, user_input: str, response: str) -> None:
        """保存对话到记忆"""
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

        # 检查总结
        summary = await self._memory.check_and_summarize(self.session_id)
        if summary:
            logger.info(f"Session {self.session_id}: 对话已自动总结")

    async def _collect_response(self, content: str) -> str:
        """收集完整响应（用于保存）"""
        return content

    async def get_history(self) -> List[Dict]:
        """获取对话历史"""
        return await self._memory.get_messages(self.session_id)

    async def clear_history(self) -> None:
        """清除对话历史"""
        await self._memory.clear_session(self.session_id)
        self._shared_state.clear()

    async def get_shared_state(self) -> Dict[str, Any]:
        """获取共享状态"""
        return self._shared_state.to_dict()

    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """获取可用工具列表"""
        return self._tool_registry.to_openapi_schema()
