"""
流式 Agent (Agentic 架构版本)

基于 Function Calling 的智能体，让 LLM 自主决策工具调用。
参考 OpenClaw Agent Loop 核心原理，支持多轮迭代工具调用。

核心流程（Agentic Loop）：
  用户输入 → 构建 messages + system prompt → LLM 决策
    ↓
  while has_tool_calls:
    执行工具 → 追加结果到 messages → 再次请求 LLM → 继续循环
    ↓
  无 tool_calls → 输出最终响应

与单轮模式的区别：
  单轮: LLM → 工具 → 总结 → 结束
  多轮: LLM → 工具 → LLM(看结果) → 可能再调工具 → ... → 最终回答
"""

import json
import logging
from typing import AsyncGenerator, List, Dict, Optional, Any

from ..llm_client import LLMClient, LLMConfig, LLMResponse, ToolCall
from ..memory.conversation import ConversationMemory, get_memory_manager
from ..memory.shared_state import SharedState, ToolResult
from ..agent.tool_registry import ToolRegistry, get_global_registry
from ..adapters.core.factory import AdapterFactory, get_global_factory
from ..agent.chain_tracker import ChainTracker
from ..agent.hooks import HookManager


logger = logging.getLogger(__name__)

# 默认最大迭代次数，防止无限循环
DEFAULT_MAX_ITERATIONS = 10


class StreamAgent:
    """
    流式 Agent (Agentic 版本)

    功能：
    - LLM Function Calling 驱动决策
    - Agent Loop：支持多轮迭代工具调用
    - 统一工具注册表管理所有能力
    - 适配器工厂执行工具
    - 调用链追踪
    - 共享状态支持
    - Skill Context 注入系统提示词
    """

    def __init__(
        self,
        session_id: str,
        llm_client: Optional[LLMClient] = None,
        memory: Optional[ConversationMemory] = None,
        tool_registry: Optional[ToolRegistry] = None,
        adapter_factory: Optional[AdapterFactory] = None,
        project_root: str = ".",
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
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
            max_iterations: Agent Loop 最大迭代次数（默认 10）
        """
        self.session_id = session_id
        self._project_root = project_root
        self._max_iterations = max_iterations

        # 核心组件
        self._llm_client = llm_client or self._create_llm_client()
        self._memory = memory or get_memory_manager()
        self._tool_registry = tool_registry or get_global_registry()
        self._adapter_factory = adapter_factory or get_global_factory()

        # 共享状态
        self._shared_state = SharedState(session_id=self.session_id)

        # 调用链追踪
        self._chain_tracker = ChainTracker()

        # 钩子管理器
        self._hooks = HookManager()

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
        self._initialized = True

    # =========================================================================
    # System Prompt 构建（Skill Context 注入）
    # =========================================================================

    def _build_system_prompt(self) -> str:
        """
        构建系统提示词

        包含：
        1. 基础角色定义
        2. Skill 上下文（SKILL.md 正文），让 LLM 理解"何时用、怎么用"
        """
        prompt_parts = [
            "你是一个智能助手，可以使用工具来完成任务。",
            "请根据用户的需求，选择合适的工具进行操作。",
            "如果需要多步操作，请逐步调用工具完成。\n",
        ]

        # 注入 Skill 上下文
        skill_tools = self._tool_registry.list_tools(
            type=None, enabled_only=True
        )
        skill_contexts = []
        for tool in skill_tools:
            metadata = getattr(tool, "metadata", None) or {}
            prose = metadata.get("prose", "")
            if prose:
                skill_contexts.append({
                    "name": tool.name,
                    "description": tool.description,
                    "prose": prose,
                })

        if skill_contexts:
            prompt_parts.append("## 可用技能指南\n")
            for ctx in skill_contexts:
                prompt_parts.append(f"### {ctx['name']}\n")
                prompt_parts.append(f"{ctx['prose']}\n\n")

        return "".join(prompt_parts)

    # =========================================================================
    # Messages 构建
    # =========================================================================

    async def _build_messages(
        self,
        user_input: str,
        include_history: bool,
    ) -> List[Dict[str, Any]]:
        """
        构建消息列表（含 system prompt）

        Args:
            user_input: 用户输入
            include_history: 是否包含对话历史

        Returns:
            消息列表，第一条为 system 消息
        """
        messages: List[Dict[str, Any]] = []

        # 系统提示词
        messages.append({
            "role": "system",
            "content": self._build_system_prompt(),
        })

        # 对话历史
        if include_history:
            history = await self._memory.get_messages(self.session_id)
            for msg in history:
                if "role" in msg and "content" in msg:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"],
                    })

        # 当前用户输入
        messages.append({"role": "user", "content": user_input})
        return messages

    # =========================================================================
    # Agentic Loop（核心循环）
    # =========================================================================

    async def chat_stream(
        self,
        user_input: str,
        include_history: bool = True,
    ) -> AsyncGenerator[str, None]:
        """
        流式对话（Agentic Loop）

        核心循环流程：
        1. 构建 messages（含 system prompt + 历史 + 用户输入）
        2. 获取工具 schema
        3. while 循环：
           a. 调用 LLM（带 tools）
           b. 如果返回 tool_calls → 执行工具，实时流式输出中间过程，追加结果，继续循环
           c. 如果无 tool_calls → 输出最终回答，break
        4. 安全退出（max_iterations）
        5. 追加签名、保存记忆

        Args:
            user_input: 用户输入
            include_history: 是否包含对话历史

        Yields:
            str: 响应文本片段（包含中间工具调用过程）
        """
        await self.initialize()

        # 1. 构建消息
        messages = await self._build_messages(user_input, include_history)

        # 2. 获取工具 schema
        tools_schema = self._tool_registry.to_openapi_schema()
        tools = tools_schema.get("tools", []) if tools_schema else None

        # 3. Agent Loop
        iteration = 0
        final_content = ""

        await self._hooks.fire("on_loop_start", messages=messages, tools=tools)

        while iteration < self._max_iterations:
            # 调用 LLM（流式）
            await self._hooks.fire("before_model_call", messages=messages, iteration=iteration)

            # === 流式调用：一次请求同时处理文本输出和 tool_calls ===
            collected_content = ""
            collected_tool_calls = {}
            tool_call_order = []
            has_tool_calls = False

            try:
                request_params = {
                    "model": self._llm_client.config.model,
                    "messages": messages,
                    "temperature": self._llm_client.config.temperature,
                    "max_tokens": self._llm_client.config.max_tokens,
                    "stream": True,
                }
                if tools:
                    request_params["tools"] = tools

                raw_stream = await self._llm_client._client.chat.completions.create(
                    **request_params
                )

                async for chunk in raw_stream:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta

                    # 文本内容：直接 yield（逐 token 推送给前端）
                    if delta.content:
                        collected_content += delta.content
                        yield delta.content

                    # Tool call delta：累积
                    if delta.tool_calls:
                        for tc_delta in delta.tool_calls:
                            tc_id = tc_delta.id
                            tc_index = tc_delta.index if hasattr(tc_delta, 'index') and tc_delta.index is not None else 0

                            if tc_index not in collected_tool_calls:
                                collected_tool_calls[tc_index] = {
                                    "id": "",
                                    "name": "",
                                    "arguments": "",
                                }
                                tool_call_order.append(tc_index)

                            entry = collected_tool_calls[tc_index]
                            if tc_id:
                                entry["id"] = tc_id
                            if hasattr(tc_delta, 'function') and tc_delta.function:
                                if tc_delta.function.name:
                                    entry["name"] += tc_delta.function.name
                                if tc_delta.function.arguments:
                                    entry["arguments"] += tc_delta.function.arguments

                    # 如果 finish_reason 是 tool_calls，标记
                    if chunk.choices[0].finish_reason == "tool_calls":
                        has_tool_calls = True

            except Exception as e:
                logger.error(f"LLM 流式调用失败: {e}")
                raise

            # 判断是否有完整的 tool_calls
            has_tool_calls = has_tool_calls or bool(collected_tool_calls)

            await self._hooks.fire("after_model_call", response=None, iteration=iteration)

            if has_tool_calls and collected_tool_calls:
                # --- 有工具调用：执行并继续循环 ---
                # 注意：文本内容已经在上面的流式中 yield 出去了

                # 追加 assistant 消息（含 tool_calls）
                tool_calls_list = []
                for idx in tool_call_order:
                    tc = collected_tool_calls[idx]
                    tool_calls_list.append({
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": tc["arguments"],
                        },
                    })

                messages.append({
                    "role": "assistant",
                    "content": collected_content or "",
                    "tool_calls": tool_calls_list,
                })

                # 执行所有工具调用
                await self._hooks.fire("before_tool_calls", tool_calls=None, iteration=iteration)
                for tc_data in tool_calls_list:
                    try:
                        tool_name = tc_data["function"]["name"]
                        # 实时流式输出工具调用信息
                        yield f"\n> 调用工具: {tool_name}\n"

                        # 解析参数
                        arguments = json.loads(tc_data["function"]["arguments"])
                        logger.info(
                            f"[Loop {iteration}] 工具调用: "
                            f"{tool_name}({arguments})"
                        )

                        # 通过工厂执行
                        result = await self._adapter_factory.route(
                            tool_name=tool_name,
                            parameters=arguments,
                            session_id=self.session_id,
                        )

                        # 记录调用链
                        self._chain_tracker.add(
                            source_type="tool",
                            source_name=tool_name,
                            confidence=1.0,
                        )

                        # 构建工具结果
                        result_data = {
                            "success": result.success,
                            "data": result.data,
                            "error": result.error,
                        }
                        result_content = json.dumps(result_data, ensure_ascii=False)

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc_data["id"],
                            "content": result_content,
                        })

                        # 实时流式输出工具结果摘要
                        if result.success:
                            data_str = str(result.data)
                            summary = (
                                data_str[:200] + "..."
                                if len(data_str) > 200
                                else data_str
                            )
                            yield f"> 工具结果: {summary}\n\n"
                        else:
                            yield f"> 工具调用失败: {result.error}\n\n"

                        # 更新共享状态
                        await self._shared_state.add_tool_result(
                            ToolResult(
                                tool_name=tool_name,
                                success=result.success,
                                data=result.data if result.success else None,
                                error=result.error,
                            )
                        )

                    except Exception as e:
                        logger.error(
                            f"工具调用失败 {tc_data['function']['name']}: {e}"
                        )
                        error_content = json.dumps(
                            {"success": False, "error": str(e)},
                            ensure_ascii=False,
                        )
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc_data["id"],
                            "content": error_content,
                        })
                        yield f"> 工具调用异常: {e}\n\n"

                iteration += 1
                logger.info(f"[Agent Loop] 完成第 {iteration} 轮工具调用")
                await self._hooks.fire("after_tool_calls", iteration=iteration)
                # 继续循环，让 LLM 看到结果后决定下一步

            else:
                # --- 无工具调用：文本已在流式中 yield，直接退出 ---
                final_content = collected_content
                break

        # 安全退出：达到最大迭代次数
        if iteration >= self._max_iterations:
            warning = "\n\n[已达到最大迭代次数，停止工具调用]"
            yield warning
            final_content += warning
            logger.warning(
                f"Session {self.session_id}: 达到最大迭代次数 "
                f"{self._max_iterations}"
            )

        await self._hooks.fire("on_loop_end", iteration=iteration)

        # 4. 追加调用链签名
        signature = self._chain_tracker.format_signature()
        if signature:
            yield signature

        # 5. 保存到记忆
        full_response = final_content
        await self._save_to_memory(user_input, full_response)

        # 6. 清理
        self._chain_tracker.clear()

        logger.info(
            f"[Agent Loop] 结束, 共 {iteration} 轮工具调用"
        )

    async def chat(
        self,
        user_input: str,
        include_history: bool = True,
    ) -> str:
        """
        非流式对话（Agentic Loop）

        Args:
            user_input: 用户输入
            include_history: 是否包含对话历史

        Returns:
            str: 完整响应
        """
        await self.initialize()

        # 构建消息
        messages = await self._build_messages(user_input, include_history)

        # 获取工具 schema
        tools_schema = self._tool_registry.to_openapi_schema()
        tools = tools_schema.get("tools", []) if tools_schema else None

        # Agent Loop
        iteration = 0

        while iteration < self._max_iterations:
            response = await self._llm_client.chat(
                messages=messages,
                tools=tools,
            )

            if response.has_tool_calls():
                # 追加 assistant 消息
                messages.append({
                    "role": "assistant",
                    "content": response.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function_name,
                                "arguments": tc.arguments,
                            },
                        }
                        for tc in response.tool_calls
                    ],
                })

                # 执行所有工具调用
                for tool_call in response.tool_calls:
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

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps({
                                "success": result.success,
                                "data": result.data,
                                "error": result.error,
                            }, ensure_ascii=False),
                        })

                        await self._shared_state.add_tool_result(
                            ToolResult(
                                tool_name=tool_call.function_name,
                                success=result.success,
                                data=result.data if result.success else None,
                                error=result.error,
                            )
                        )

                    except Exception as e:
                        logger.error(
                            f"工具调用失败 {tool_call.function_name}: {e}"
                        )
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(
                                {"success": False, "error": str(e)},
                                ensure_ascii=False,
                            ),
                        })

                iteration += 1
                # 继续循环

            else:
                # 无工具调用，返回最终回答
                full_response = response.content or ""

                # 追加签名
                signature = self._chain_tracker.format_signature()
                full_response += signature

                # 保存记忆
                await self._save_to_memory(user_input, full_response)

                # 清理
                self._chain_tracker.clear()

                return full_response

        # 达到最大迭代次数
        full_response = "[已达到最大迭代次数，停止工具调用]"
        signature = self._chain_tracker.format_signature()
        full_response += signature

        await self._save_to_memory(user_input, full_response)
        self._chain_tracker.clear()

        return full_response

    # =========================================================================
    # 记忆管理
    # =========================================================================

    async def _save_to_memory(self, user_input: str, response: str) -> None:
        """保存对话到记忆"""
        await self._memory.add_message(
            session_id=self.session_id,
            role="user",
            content=user_input,
        )
        await self._memory.add_message(
            session_id=self.session_id,
            role="assistant",
            content=response,
        )

        # 检查总结
        summary = await self._memory.check_and_summarize(self.session_id)
        if summary:
            logger.info(f"Session {self.session_id}: 对话已自动总结")

    # =========================================================================
    # 辅助方法
    # =========================================================================

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
