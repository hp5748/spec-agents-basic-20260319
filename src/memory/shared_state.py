"""
SharedState - 主子 Agent 上下文共享机制

实现轻量级、线程安全的上下文共享机制，支持：
- messages: 对话消息列表
- tool_results: 工具执行结果
- context_vars: 上下文变量（键值对）

使用 asyncio.Lock 实现并发安全，支持持久化到 Memory。
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json


logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """工具执行结果"""
    tool_name: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolResult":
        """从字典创建"""
        return cls(
            tool_name=data["tool_name"],
            success=data["success"],
            data=data.get("data"),
            error=data.get("error"),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            metadata=data.get("metadata", {})
        )


@dataclass
class SharedSnapshot:
    """共享状态快照"""
    session_id: str
    messages: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    context_vars: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    version: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "messages": self.messages,
            "tool_results": self.tool_results,
            "context_vars": self.context_vars,
            "timestamp": self.timestamp,
            "version": self.version
        }


class SharedState:
    """
    共享状态管理器

    功能：
    - 存储 messages、tool_results、context_vars
    - 使用 asyncio.Lock 保证线程安全
    - 支持状态快照和恢复
    - 内存占用可控（自动限制历史记录）

    使用方式：
        # 创建共享状态
        state = SharedState(session_id="test_session")

        # 添加消息
        await state.add_message({"role": "user", "content": "Hello"})

        # 添加工具结果
        await state.add_tool_result(ToolResult(...))

        # 设置上下文变量
        await state.set_context_var("user_name", "Alice")

        # 获取状态
        messages = await state.get_messages()
        results = await state.get_tool_results()
        name = await state.get_context_var("user_name")

        # 创建快照
        snapshot = await state.create_snapshot()

        # 从快照恢复
        await state.restore_from_snapshot(snapshot)

        # 清空状态
        await state.clear()
    """

    def __init__(
        self,
        session_id: str,
        max_messages: int = 1000,
        max_tool_results: int = 500,
        max_context_vars: int = 100
    ):
        """
        初始化共享状态

        Args:
            session_id: 会话 ID
            max_messages: 最大消息数量
            max_tool_results: 最大工具结果数量
            max_context_vars: 最大上下文变量数量
        """
        self.session_id = session_id
        self._max_messages = max_messages
        self._max_tool_results = max_tool_results
        self._max_context_vars = max_context_vars

        # 数据存储
        self._messages: List[Dict[str, Any]] = []
        self._tool_results: List[ToolResult] = []
        self._context_vars: Dict[str, Any] = {}

        # 并发控制
        self._lock = asyncio.Lock()

        # 版本号（用于快照）
        self._version = 0

        logger.debug(
            f"SharedState 初始化: session={session_id}, "
            f"max_messages={max_messages}, max_results={max_tool_results}"
        )

    # ========== Messages 操作 ==========

    async def add_message(self, message: Dict[str, Any]) -> None:
        """
        添加消息

        Args:
            message: 消息字典，包含 role、content 等
        """
        async with self._lock:
            # 添加时间戳
            if "timestamp" not in message:
                message["timestamp"] = datetime.now().isoformat()

            self._messages.append(message)

            # 限制消息数量
            if len(self._messages) > self._max_messages:
                removed = len(self._messages) - self._max_messages
                self._messages = self._messages[-self._max_messages:]
                logger.debug(
                    f"Session {self.session_id}: 消息数量超限，"
                    f"移除 {removed} 条旧消息"
                )

            self._version += 1
            logger.debug(
                f"Session {self.session_id}: 添加消息 [{message.get('role')}], "
                f"总数: {len(self._messages)}"
            )

    async def get_messages(
        self,
        limit: Optional[int] = None,
        role: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取消息列表

        Args:
            limit: 限制返回数量
            role: 按角色过滤 (user/assistant/system)

        Returns:
            消息列表
        """
        async with self._lock:
            messages = self._messages.copy()

            # 按角色过滤
            if role:
                messages = [m for m in messages if m.get("role") == role]

            # 限制数量
            if limit:
                messages = messages[-limit:]

            return messages

    async def get_last_message(self, role: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        获取最后一条消息

        Args:
            role: 按角色过滤

        Returns:
            最后一条消息，如果不存在则返回 None
        """
        async with self._lock:
            if not self._messages:
                return None

            if role:
                # 查找指定角色的最后一条消息
                for msg in reversed(self._messages):
                    if msg.get("role") == role:
                        return msg.copy()
                return None

            return self._messages[-1].copy()

    async def get_message_count(self) -> int:
        """获取消息数量"""
        async with self._lock:
            return len(self._messages)

    # ========== Tool Results 操作 ==========

    async def add_tool_result(self, result: ToolResult) -> None:
        """
        添加工具执行结果

        Args:
            result: 工具结果对象
        """
        async with self._lock:
            self._tool_results.append(result)

            # 限制结果数量
            if len(self._tool_results) > self._max_tool_results:
                removed = len(self._tool_results) - self._max_tool_results
                self._tool_results = self._tool_results[-self._max_tool_results:]
                logger.debug(
                    f"Session {self.session_id}: 工具结果数量超限，"
                    f"移除 {removed} 条旧结果"
                )

            self._version += 1
            logger.debug(
                f"Session {self.session_id}: 添加工具结果 [{result.tool_name}], "
                f"success={result.success}, 总数: {len(self._tool_results)}"
            )

    async def get_tool_results(
        self,
        tool_name: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[ToolResult]:
        """
        获取工具结果列表

        Args:
            tool_name: 按工具名称过滤
            limit: 限制返回数量

        Returns:
            工具结果列表
        """
        async with self._lock:
            results = self._tool_results.copy()

            # 按工具名称过滤
            if tool_name:
                results = [r for r in results if r.tool_name == tool_name]

            # 限制数量
            if limit:
                results = results[-limit:]

            return results

    async def get_last_tool_result(self, tool_name: Optional[str] = None) -> Optional[ToolResult]:
        """
        获取最后一个工具结果

        Args:
            tool_name: 按工具名称过滤

        Returns:
            最后一个工具结果，如果不存在则返回 None
        """
        async with self._lock:
            if not self._tool_results:
                return None

            if tool_name:
                # 查找指定工具的最后一个结果
                for result in reversed(self._tool_results):
                    if result.tool_name == tool_name:
                        return result
                return None

            return self._tool_results[-1]

    async def get_tool_result_count(self, tool_name: Optional[str] = None) -> int:
        """
        获取工具结果数量

        Args:
            tool_name: 按工具名称过滤

        Returns:
            结果数量
        """
        async with self._lock:
            if tool_name:
                return sum(1 for r in self._tool_results if r.tool_name == tool_name)
            return len(self._tool_results)

    async def clear_tool_results(self, tool_name: Optional[str] = None) -> None:
        """
        清除工具结果

        Args:
            tool_name: 按工具名称过滤，None 表示清除所有
        """
        async with self._lock:
            if tool_name:
                self._tool_results = [r for r in self._tool_results if r.tool_name != tool_name]
                logger.debug(f"Session {self.session_id}: 清除工具 [{tool_name}] 的结果")
            else:
                self._tool_results.clear()
                logger.debug(f"Session {self.session_id}: 清除所有工具结果")

            self._version += 1

    # ========== Context Vars 操作 ==========

    async def set_context_var(self, key: str, value: Any) -> None:
        """
        设置上下文变量

        Args:
            key: 变量名
            value: 变量值
        """
        async with self._lock:
            self._context_vars[key] = value

            # 限制变量数量
            if len(self._context_vars) > self._max_context_vars:
                # 移除最早设置的变量（保留后设置的）
                removed_keys = list(self._context_vars.keys())[:-self._max_context_vars]
                for k in removed_keys:
                    del self._context_vars[k]
                logger.debug(
                    f"Session {self.session_id}: 上下文变量数量超限，"
                    f"移除 {len(removed_keys)} 个变量"
                )

            self._version += 1
            logger.debug(
                f"Session {self.session_id}: 设置上下文变量 {key}={value}, "
                f"总数: {len(self._context_vars)}"
            )

    async def get_context_var(self, key: str, default: Any = None) -> Any:
        """
        获取上下文变量

        Args:
            key: 变量名
            default: 默认值

        Returns:
            变量值，如果不存在则返回默认值
        """
        async with self._lock:
            return self._context_vars.get(key, default)

    async def get_all_context_vars(self) -> Dict[str, Any]:
        """获取所有上下文变量"""
        async with self._lock:
            return self._context_vars.copy()

    async def remove_context_var(self, key: str) -> bool:
        """
        移除上下文变量

        Args:
            key: 变量名

        Returns:
            是否成功移除
        """
        async with self._lock:
            if key in self._context_vars:
                del self._context_vars[key]
                self._version += 1
                logger.debug(f"Session {self.session_id}: 移除上下文变量 {key}")
                return True
            return False

    async def clear_context_vars(self) -> None:
        """清除所有上下文变量"""
        async with self._lock:
            self._context_vars.clear()
            self._version += 1
            logger.debug(f"Session {self.session_id}: 清除所有上下文变量")

    # ========== 快照和恢复 ==========

    async def create_snapshot(self) -> SharedSnapshot:
        """
        创建状态快照

        Returns:
            SharedSnapshot 对象
        """
        async with self._lock:
            snapshot = SharedSnapshot(
                session_id=self.session_id,
                messages=[msg.copy() for msg in self._messages],
                tool_results=[result.to_dict() for result in self._tool_results],
                context_vars=self._context_vars.copy(),
                timestamp=datetime.now().isoformat(),
                version=self._version
            )

            logger.debug(
                f"Session {self.session_id}: 创建快照 v{self._version}, "
                f"messages={len(self._messages)}, results={len(self._tool_results)}, "
                f"vars={len(self._context_vars)}"
            )

            return snapshot

    async def restore_from_snapshot(self, snapshot: SharedSnapshot) -> None:
        """
        从快照恢复状态

        Args:
            snapshot: SharedSnapshot 对象
        """
        async with self._lock:
            self._messages = [msg.copy() for msg in snapshot.messages]
            self._tool_results = [
                ToolResult.from_dict(data) for data in snapshot.tool_results
            ]
            self._context_vars = snapshot.context_vars.copy()
            self._version = snapshot.version

            logger.info(
                f"Session {self.session_id}: 从快照恢复 v{snapshot.version}, "
                f"messages={len(self._messages)}, results={len(self._tool_results)}, "
                f"vars={len(self._context_vars)}"
            )

    async def restore_from_dict(self, data: Dict[str, Any]) -> None:
        """
        从字典恢复状态

        Args:
            data: 包含状态数据的字典
        """
        snapshot = SharedSnapshot(
            session_id=data.get("session_id", self.session_id),
            messages=data.get("messages", []),
            tool_results=data.get("tool_results", []),
            context_vars=data.get("context_vars", {}),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            version=data.get("version", 0)
        )

        await self.restore_from_snapshot(snapshot)

    # ========== 清空和状态查询 ==========

    async def clear(self) -> None:
        """清空所有状态"""
        async with self._lock:
            self._messages.clear()
            self._tool_results.clear()
            self._context_vars.clear()
            self._version += 1
            logger.info(f"Session {self.session_id}: 清空所有状态")

    async def is_empty(self) -> bool:
        """检查状态是否为空"""
        async with self._lock:
            return (
                len(self._messages) == 0
                and len(self._tool_results) == 0
                and len(self._context_vars) == 0
            )

    async def get_stats(self) -> Dict[str, Any]:
        """获取状态统计信息"""
        async with self._lock:
            return {
                "session_id": self.session_id,
                "message_count": len(self._messages),
                "tool_result_count": len(self._tool_results),
                "context_var_count": len(self._context_vars),
                "version": self._version,
                "max_messages": self._max_messages,
                "max_tool_results": self._max_tool_results,
                "max_context_vars": self._max_context_vars
            }

    async def to_dict(self) -> Dict[str, Any]:
        """导出为字典（用于持久化）"""
        async with self._lock:
            return {
                "session_id": self.session_id,
                "messages": [msg.copy() for msg in self._messages],
                "tool_results": [result.to_dict() for result in self._tool_results],
                "context_vars": self._context_vars.copy(),
                "version": self._version,
                "timestamp": datetime.now().isoformat()
            }


# 全局共享状态管理器
_shared_states: Dict[str, SharedState] = {}
_states_lock = asyncio.Lock()


async def get_shared_state(
    session_id: str,
    max_messages: int = 1000,
    max_tool_results: int = 500,
    max_context_vars: int = 100
) -> SharedState:
    """
    获取或创建共享状态实例

    Args:
        session_id: 会话 ID
        max_messages: 最大消息数量
        max_tool_results: 最大工具结果数量
        max_context_vars: 最大上下文变量数量

    Returns:
        SharedState 实例
    """
    async with _states_lock:
        if session_id not in _shared_states:
            _shared_states[session_id] = SharedState(
                session_id=session_id,
                max_messages=max_messages,
                max_tool_results=max_tool_results,
                max_context_vars=max_context_vars
            )
            logger.debug(f"创建 SharedState: {session_id}")

        return _shared_states[session_id]


async def remove_shared_state(session_id: str) -> bool:
    """
    移除共享状态实例

    Args:
        session_id: 会话 ID

    Returns:
        是否成功移除
    """
    async with _states_lock:
        if session_id in _shared_states:
            del _shared_states[session_id]
            logger.debug(f"移除 SharedState: {session_id}")
            return True
        return False


async def list_shared_states() -> List[str]:
    """列出所有共享状态的会话 ID"""
    async with _states_lock:
        return list(_shared_states.keys())


async def clear_all_shared_states() -> None:
    """清空所有共享状态"""
    async with _states_lock:
        _shared_states.clear()
        logger.info("清空所有 SharedState")
