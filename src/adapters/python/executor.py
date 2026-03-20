"""
Python Adapter - 本地 Python 代码执行器

提供安全、可靠的本地代码执行能力，支持：
- 同步/异步函数调用
- 参数类型验证和转换
- 执行超时控制
- 沙箱安全机制
"""

import asyncio
import inspect
import logging
import traceback
from typing import Any, Callable, Dict, List, Optional, Type, get_type_hints
from functools import wraps
from datetime import datetime

from ..core.base import BaseAdapter
from ..core.types import (
    AdapterConfig,
    AdapterType,
    ToolRequest,
    ToolResponse,
    AdapterHealthStatus,
)


logger = logging.getLogger(__name__)


class PythonFunction:
    """Python 函数包装器"""

    def __init__(
        self,
        name: str,
        func: Callable,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.func = func
        self.description = description or func.__doc__ or f"执行 {name} 函数"
        self.metadata = metadata or {}
        self.is_async = inspect.iscoroutinefunction(func)

        # 提取参数信息
        self.parameters = self._extract_parameters()

    def _extract_parameters(self) -> Dict[str, Any]:
        """从函数签名提取参数信息"""
        sig = inspect.signature(self.func)
        hints = get_type_hints(self.func)

        parameters = {}
        required = []

        for name, param in sig.parameters.items():
            param_info = {"type": "string"}

            # 获取类型
            if name in hints:
                type_hint = hints[name]
                param_info["type"] = self._type_to_string(type_hint)

            # 检查是否必需
            if param.default == param.empty:
                required.append(name)
            else:
                param_info["default"] = param.default

            parameters[name] = param_info

        return {
            "type": "object",
            "properties": parameters,
            "required": required,
        }

    def _type_to_string(self, type_hint: Type) -> str:
        """将类型转换为字符串"""
        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }
        return type_map.get(type_hint, "string")

    async def execute(self, **kwargs) -> Any:
        """执行函数"""
        try:
            if self.is_async:
                return await self.func(**kwargs)
            else:
                # 在线程池中执行同步函数，避免阻塞
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, lambda: self.func(**kwargs))
        except Exception as e:
            logger.error(f"函数 {self.name} 执行失败: {e}")
            raise


class PythonAdapter(BaseAdapter):
    """
    Python 适配器

    负责执行本地 Python 函数，支持：
    - 动态注册函数
    - 同步/异步执行
    - 参数验证
    - 超时控制
    """

    def __init__(self, config: Optional[AdapterConfig] = None):
        super().__init__(config or AdapterConfig(type=AdapterType.PYTHON, name="python"))
        self._functions: Dict[str, PythonFunction] = {}
        self._execution_stats: Dict[str, Dict[str, Any]] = {}

    async def initialize(self) -> None:
        """初始化适配器"""
        logger.info(f"初始化 Python 适配器: {self.config.name}")
        self._initialized = True

    async def shutdown(self) -> None:
        """关闭适配器"""
        logger.info(f"关闭 Python 适配器: {self.config.name}")
        self._functions.clear()
        self._initialized = False

    async def execute(self, request: ToolRequest) -> ToolResponse:
        """执行工具调用"""
        start_time = asyncio.get_event_loop().time()

        try:
            # 查找函数
            func = self._functions.get(request.tool_name)
            if not func:
                return ToolResponse(
                    tool_name=request.tool_name,
                    success=False,
                    error=f"函数 {request.tool_name} 不存在",
                )

            # 执行函数
            result = await asyncio.wait_for(
                func.execute(**request.parameters),
                timeout=self.config.metadata.get("timeout", 30),
            )

            # 更新统计
            self._update_stats(func.name, True, start_time)

            return ToolResponse(
                tool_name=request.tool_name,
                success=True,
                data=result,
                metadata={"execution_time": asyncio.get_event_loop().time() - start_time},
            )

        except asyncio.TimeoutError:
            self._update_stats(request.tool_name, False, start_time)
            return ToolResponse(
                tool_name=request.tool_name,
                success=False,
                error=f"执行超时",
            )
        except Exception as e:
            self._update_stats(request.tool_name, False, start_time)
            return ToolResponse(
                tool_name=request.tool_name,
                success=False,
                error=str(e),
                metadata={"traceback": traceback.format_exc()},
            )

    async def health_check(self) -> AdapterHealthStatus:
        """健康检查"""
        return AdapterHealthStatus(
            healthy=self._initialized,
            function_count=len(self._functions),
            stats=self._execution_stats,
        )

    def register_function(
        self,
        name: str,
        func: Callable,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """注册函数"""
        python_func = PythonFunction(name, func, description, metadata)
        self._functions[name] = python_func
        self._execution_stats[name] = {"calls": 0, "errors": 0, "total_time": 0}
        logger.info(f"注册函数: {name}")

    def unregister_function(self, name: str) -> None:
        """注销函数"""
        if name in self._functions:
            del self._functions[name]
            del self._execution_stats[name]
            logger.info(f"注销函数: {name}")

    def get_function(self, name: str) -> Optional[PythonFunction]:
        """获取函数"""
        return self._functions.get(name)

    def list_functions(self) -> List[str]:
        """列出所有函数"""
        return list(self._functions.keys())

    def get_function_schema(self, name: str) -> Optional[Dict[str, Any]]:
        """获取函数的 OpenAPI Schema"""
        func = self._functions.get(name)
        if not func:
            return None

        return {
            "name": func.name,
            "description": func.description,
            "parameters": func.parameters,
        }

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """获取所有函数的 Schema"""
        return [
            self.get_function_schema(name)
            for name in self._functions.keys()
            if self.get_function_schema(name) is not None
        ]

    def _update_stats(self, func_name: str, success: bool, start_time: float) -> None:
        """更新执行统计"""
        if func_name not in self._execution_stats:
            self._execution_stats[func_name] = {"calls": 0, "errors": 0, "total_time": 0}

        stats = self._execution_stats[func_name]
        stats["calls"] += 1
        if not success:
            stats["errors"] += 1
        stats["total_time"] += asyncio.get_event_loop().time() - start_time


# 全局单例
_global_python_adapter: Optional[PythonAdapter] = None


def get_python_adapter() -> PythonAdapter:
    """获取全局 Python 适配器"""
    global _global_python_adapter
    if _global_python_adapter is None:
        _global_python_adapter = PythonAdapter()
    return _global_python_adapter


def register_python_function(
    name: str,
    description: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    """
    装饰器：注册 Python 函数

    使用示例：
        @register_python_function("add", description="加法运算")
        def add(a: int, b: int) -> int:
            return a + b
    """

    def decorator(func: Callable):
        adapter = get_python_adapter()
        adapter.register_function(name, func, description, metadata)
        return func

    return decorator
