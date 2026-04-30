"""
Agent Loop 钩子管理器

参考 OpenClaw Agent Loop 的 hook points 设计，
在循环的关键位置提供可扩展的钩子点。

支持的钩子事件：
- before_model_call: LLM 调用前
- after_model_call: LLM 调用后
- before_tool_calls: 工具调用前
- after_tool_calls: 工具调用后
- on_loop_start: Agent Loop 开始
- on_loop_end: Agent Loop 结束
"""

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class HookManager:
    """
    Agent Loop 钩子管理器

    使用方式：
        hooks = HookManager()

        # 注册钩子
        @hooks.on("before_tool_calls")
        async def log_tool_calls(tool_calls, **kwargs):
            for tc in tool_calls:
                print(f"即将调用: {tc.function_name}")

        # 或者直接注册
        hooks.register("after_tool_calls", my_callback)
    """

    def __init__(self):
        self._hooks: Dict[str, List[Callable]] = {}

    def register(self, event: str, callback: Callable) -> None:
        """
        注册钩子回调

        Args:
            event: 事件名称
            callback: 异步回调函数，接收 **kwargs
        """
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(callback)
        logger.debug(f"已注册钩子: {event} -> {callback.__name__}")

    def on(self, event: str) -> Callable:
        """
        装饰器方式注册钩子

        Args:
            event: 事件名称

        Returns:
            装饰器函数

        示例：
            @hooks.on("before_tool_calls")
            async def my_hook(tool_calls, **kwargs):
                pass
        """
        def decorator(func: Callable) -> Callable:
            self.register(event, func)
            return func
        return decorator

    async def fire(self, event: str, **kwargs: Any) -> None:
        """
        触发钩子事件

        Args:
            event: 事件名称
            **kwargs: 传递给回调的参数
        """
        callbacks = self._hooks.get(event, [])
        for callback in callbacks:
            try:
                await callback(**kwargs)
            except Exception as e:
                logger.warning(f"Hook [{event}] {callback.__name__} 执行失败: {e}")

    def clear(self, event: Optional[str] = None) -> None:
        """
        清除钩子

        Args:
            event: 事件名称（None 表示清除全部）
        """
        if event:
            self._hooks.pop(event, None)
        else:
            self._hooks.clear()

    def list_hooks(self) -> Dict[str, int]:
        """列出已注册的钩子数量"""
        return {event: len(callbacks) for event, callbacks in self._hooks.items()}
