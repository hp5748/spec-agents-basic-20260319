"""
LLM 客户端

支持 OpenAI 兼容 API（如硅基流动、DeepSeek 等）
支持 Function Calling (tools/tool_calls)
"""

import os
from typing import Any, Dict, List, Optional, AsyncGenerator, Union
from dataclasses import dataclass
import logging

try:
    from openai import AsyncOpenAI
    from openai.types.chat import ChatCompletionMessageToolCall
except ImportError:
    AsyncOpenAI = None
    ChatCompletionMessageToolCall = None


logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """工具调用"""
    id: str
    function_name: str
    arguments: str

    @classmethod
    def from_openai(cls, tool_call: Any) -> "ToolCall":
        """从 OpenAI tool_call 创建"""
        return cls(
            id=tool_call.id,
            function_name=tool_call.function.name,
            arguments=tool_call.function.arguments,
        )


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: Optional[str]
    tool_calls: Optional[List[ToolCall]] = None

    def has_tool_calls(self) -> bool:
        """是否有工具调用"""
        return bool(self.tool_calls)


@dataclass
class LLMConfig:
    """LLM 配置"""
    api_key: str
    base_url: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 4096

    @classmethod
    def from_env(cls, prefix: str = "SILICONFLOW") -> "LLMConfig":
        """从环境变量加载配置"""
        return cls(
            api_key=os.getenv(f"{prefix}_API_KEY", ""),
            base_url=os.getenv(f"{prefix}_BASE_URL", "https://api.siliconflow.cn/v1"),
            model=os.getenv(f"{prefix}_MODEL", "deepseek-ai/DeepSeek-V3"),
        )


class LLMClient:
    """
    LLM 客户端

    支持 OpenAI 兼容 API，可用于：
    - 硅基流动 (SiliconFlow)
    - DeepSeek
    - OpenAI
    - 其他兼容 API
    """

    def __init__(self, config: LLMConfig):
        if AsyncOpenAI is None:
            raise ImportError("请安装 openai: pip install openai")

        self.config = config
        self._client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
        )

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> LLMResponse:
        """
        发送聊天请求

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大 token 数
            tools: 工具列表（Function Calling）

        Returns:
            LLMResponse: 助手回复（可能包含 tool_calls）
        """
        try:
            request_params = {
                "model": self.config.model,
                "messages": messages,
                "temperature": temperature or self.config.temperature,
                "max_tokens": max_tokens or self.config.max_tokens,
            }

            if tools:
                request_params["tools"] = tools

            response = await self._client.chat.completions.create(
                **request_params,
                **kwargs
            )

            message = response.choices[0].message

            # 处理工具调用
            tool_calls = None
            if hasattr(message, "tool_calls") and message.tool_calls:
                tool_calls = [
                    ToolCall.from_openai(tc) for tc in message.tool_calls
                ]

            return LLMResponse(
                content=message.content,
                tool_calls=tool_calls,
            )
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        流式聊天

        Yields:
            str: 文本片段
        """
        try:
            stream = await self._client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=temperature or self.config.temperature,
                max_tokens=max_tokens or self.config.max_tokens,
                stream=True,
                **kwargs
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"LLM 流式调用失败: {e}")
            raise

    async def test_connection(self) -> bool:
        """测试 API 连接"""
        try:
            response = await self.chat(
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            return bool(response)
        except Exception as e:
            logger.error(f"API 连接测试失败: {e}")
            return False
