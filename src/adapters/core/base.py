"""
Adapter 基类

定义所有适配器必须实现的基础接口。
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional

from .types import (
    AdapterConfig,
    AdapterCapabilities,
    AdapterHealthStatus,
    AdapterType,
    ToolRequest,
    ToolResponse
)


logger = logging.getLogger(__name__)


class BaseAdapter(ABC):
    """
    适配器基类

    所有适配器必须继承此类并实现核心方法。

    设计原则：
    1. 统一接口：所有适配器遵循相同的执行接口
    2. 异步优先：所有核心方法都是异步的
    3. 错误处理：统一的错误处理和降级策略
    4. 健康检查：支持健康状态监控
    5. 可观测性：内置调用链追踪和性能监控
    """

    def __init__(self, config: AdapterConfig):
        """
        初始化适配器

        Args:
            config: 适配器配置
        """
        self.config = config
        self._health_status = AdapterHealthStatus(healthy=True)
        self._capabilities = AdapterCapabilities()
        self._error_count = 0
        self._lock = asyncio.Lock()

    @abstractmethod
    async def initialize(self) -> None:
        """
        初始化适配器

        在适配器首次使用前调用，用于建立连接、加载资源等。
        """
        pass

    @abstractmethod
    async def execute(self, request: ToolRequest) -> ToolResponse:
        """
        执行工具调用

        Args:
            request: 工具调用请求

        Returns:
            ToolResponse: 执行响应
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """
        关闭适配器

        释放资源、断开连接等。
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> AdapterCapabilities:
        """
        获取适配器能力描述

        Returns:
            AdapterCapabilities: 能力描述
        """
        pass

    async def health_check(self) -> AdapterHealthStatus:
        """
        健康检查

        默认实现：检查错误计数

        Returns:
            AdapterHealthStatus: 健康状态
        """
        self._health_status.last_check = time.time()
        self._health_status.error_count = self._error_count

        # 简单的健康判断：错误计数 < 10 认为健康
        self._health_status.healthy = self._error_count < 10

        if self._health_status.healthy:
            self._health_status.message = "Adapter is healthy"
        else:
            self._health_status.message = f"Adapter has {self._error_count} errors"

        return self._health_status

    async def execute_batch(
        self,
        requests: List[ToolRequest]
    ) -> List[ToolResponse]:
        """
        批量执行工具调用

        默认实现：顺序执行每个请求

        Args:
            requests: 工具调用请求列表

        Returns:
            List[ToolResponse]: 响应列表
        """
        responses = []
        for request in requests:
            response = await self.execute(request)
            responses.append(response)
        return responses

    async def execute_stream(
        self,
        request: ToolRequest
    ) -> AsyncGenerator[str, None]:
        """
        流式执行工具调用

        默认实现：调用 execute() 并分块返回

        Args:
            request: 工具调用请求

        Yields:
            str: 响应片段
        """
        response = await self.execute(request)

        if response.success and isinstance(response.data, str):
            # 逐字符返回
            for char in response.data:
                yield char
        elif response.success:
            # 非字符串数据转换为 JSON
            import json
            yield json.dumps(response.data, ensure_ascii=False)
        else:
            # 错误信息
            yield response.error or "Unknown error"

    async def list_tools(self) -> List[str]:
        """
        列出适配器支持的所有工具

        默认实现：返回配置中的工具列表

        Returns:
            List[str]: 工具名称列表
        """
        return self._capabilities.tools

    def _increment_error_count(self) -> None:
        """增加错误计数"""
        self._error_count += 1

    def _reset_error_count(self) -> None:
        """重置错误计数"""
        self._error_count = 0

    def _create_response(
        self,
        success: bool,
        data: Any = None,
        error: Optional[str] = None,
        execution_time: float = 0.0,
        chain_info: Optional[List[str]] = None
    ) -> ToolResponse:
        """
        创建工具响应

        Args:
            success: 是否成功
            data: 返回数据
            error: 错误信息
            execution_time: 执行时间
            chain_info: 调用链信息

        Returns:
            ToolResponse: 响应对象
        """
        return ToolResponse(
            success=success,
            data=data,
            error=error,
            adapter_type=self.config.type.value,
            tool_name="",
            execution_time=execution_time,
            source_type="adapter",
            source_name=self.config.name,
            chain_info=chain_info or []
        )

    async def _execute_with_tracking(
        self,
        tool_name: str,
        func: callable,
        *args,
        **kwargs
    ) -> ToolResponse:
        """
        带追踪的执行包装器

        自动记录执行时间和错误

        Args:
            tool_name: 工具名称
            func: 执行函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            ToolResponse: 执行响应
        """
        start_time = time.time()

        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time

            # 如果结果是 ToolResponse，直接返回
            if isinstance(result, ToolResponse):
                result.execution_time = execution_time
                result.adapter_type = self.config.type.value
                result.source_name = self.config.name
                return result

            # 否则包装成 ToolResponse
            return self._create_response(
                success=True,
                data=result,
                execution_time=execution_time
            )

        except Exception as e:
            execution_time = time.time() - start_time
            self._increment_error_count()
            logger.error(f"Adapter 执行失败 [{self.config.name}/{tool_name}]: {e}", exc_info=True)

            return self._create_response(
                success=False,
                error=str(e),
                execution_time=execution_time
            )

    def get_config(self) -> AdapterConfig:
        """获取适配器配置"""
        return self.config

    def is_enabled(self) -> bool:
        """判断适配器是否启用"""
        return self.config.enabled

    async def validate_request(self, request: ToolRequest) -> bool:
        """
        验证请求是否有效

        默认实现：基本验证

        Args:
            request: 工具调用请求

        Returns:
            bool: 是否有效
        """
        if not request.tool_name:
            return False

        if not self.config.enabled:
            return False

        return True


class MockAdapter(BaseAdapter):
    """
    Mock 适配器（用于测试）

    模拟一个简单的适配器实现。
    """

    def __init__(self, config: AdapterConfig):
        super().__init__(config)
        self._tools = {
            "echo": self._echo,
            "add": self._add,
            "fail": self._fail
        }
        self._capabilities = AdapterCapabilities(
            supports_streaming=False,
            supports_batch=True,
            supports_async=True,
            max_concurrent=10,
            tools=list(self._tools.keys())
        )

    async def initialize(self) -> None:
        """初始化"""
        logger.info(f"MockAdapter [{self.config.name}] initialized")

    async def execute(self, request: ToolRequest) -> ToolResponse:
        """执行工具调用"""
        if not await self.validate_request(request):
            return ToolResponse.from_error("Invalid request", request.tool_name)

        tool_func = self._tools.get(request.tool_name)
        if not tool_func:
            return ToolResponse.from_error(f"Tool not found: {request.tool_name}", request.tool_name)

        return await self._execute_with_tracking(
            request.tool_name,
            tool_func,
            request
        )

    async def shutdown(self) -> None:
        """关闭"""
        logger.info(f"MockAdapter [{self.config.name}] shutdown")

    def get_capabilities(self) -> AdapterCapabilities:
        """获取能力描述"""
        return self._capabilities

    async def _echo(self, request: ToolRequest) -> ToolResponse:
        """Echo 工具"""
        message = request.parameters.get("message", "")
        return ToolResponse.from_success(f"Echo: {message}", request.tool_name)

    async def _add(self, request: ToolRequest) -> ToolResponse:
        """加法工具"""
        a = request.parameters.get("a", 0)
        b = request.parameters.get("b", 0)
        return ToolResponse.from_success({"result": a + b}, request.tool_name)

    async def _fail(self, request: ToolRequest) -> ToolResponse:
        """失败工具（用于测试错误处理）"""
        raise ValueError("This tool always fails")
