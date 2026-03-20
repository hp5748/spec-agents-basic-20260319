"""
调用链追踪器

用于追踪 Agent 请求的处理路径，并在响应中显示调用来源。
"""

import logging
from dataclasses import dataclass
from typing import List


logger = logging.getLogger(__name__)


@dataclass
class ChainInfo:
    """
    调用链节点信息

    Attributes:
        source_type: 来源类型 ("skill", "subagent", "mcp", "llm")
        source_name: 模块名称
        confidence: 匹配置信度 0.0-1.0
    """
    source_type: str
    source_name: str
    confidence: float = 0.0

    def format(self) -> str:
        """
        格式化为显示文本

        Returns:
            str: 格式化后的显示文本
        """
        if self.source_type == "skill":
            return f"Skill: {self.source_name}"
        elif self.source_type == "subagent":
            return f"SubAgent: {self.source_name}"
        elif self.source_type == "mcp":
            return f"MCP: {self.source_name}"
        elif self.source_type == "llm":
            return "LLM"
        return self.source_name


class ChainTracker:
    """
    调用链追踪器

    用于追踪请求经过的模块路径，并格式化为用户可读的签名。

    使用示例:
        tracker = ChainTracker()
        tracker.add("skill", "sqlite-query-skill", 0.95)
        signature = tracker.format_signature()  # "\n\n[Skill: sqlite-query-skill]"
        tracker.clear()
    """

    def __init__(self):
        """初始化追踪器"""
        self._chain: List[ChainInfo] = []

    def add(self, source_type: str, source_name: str, confidence: float = 0.0) -> None:
        """
        添加调用链节点

        Args:
            source_type: 来源类型
            source_name: 模块名称
            confidence: 匹配置信度
        """
        self._chain.append(ChainInfo(source_type, source_name, confidence))
        logger.debug(f"调用链: + {source_type}:{source_name} (confidence={confidence:.2f})")

    def format_signature(self) -> str:
        """
        格式化调用链签名

        如果调用链为空，返回 LLM 标识。
        如果有调用链，返回格式化的签名。

        Returns:
            str: 格式化后的调用链签名
        """
        if not self._chain:
            return "\n\n[LLM]"

        parts = [info.format() for info in self._chain]
        return f"\n\n[{' → '.join(parts)}]"

    def is_empty(self) -> bool:
        """
        检查调用链是否为空

        Returns:
            bool: 调用链是否为空
        """
        return len(self._chain) == 0

    def clear(self) -> None:
        """清空调用链"""
        self._chain.clear()
        logger.debug("调用链已清空")

    def get_chain(self) -> List[ChainInfo]:
        """
        获取调用链副本

        Returns:
            List[ChainInfo]: 调用链副本
        """
        return list(self._chain)

    def get_summary(self) -> dict:
        """
        获取调用链摘要统计

        Returns:
            dict: 包含 total_calls 和 by_type 的统计信息
        """
        from collections import Counter

        total_calls = len(self._chain)
        type_counts = Counter(info.source_type for info in self._chain)

        return {
            "total_calls": total_calls,
            "by_type": dict(type_counts)
        }

    def __len__(self) -> int:
        """返回调用链长度"""
        return len(self._chain)

    def __repr__(self) -> str:
        """返回调用链的字符串表示"""
        if not self._chain:
            return "ChainTracker(empty)"
        parts = [info.format() for info in self._chain]
        return f"ChainTracker({' → '.join(parts)})"
