"""
MCP 工具意图匹配器

负责将用户输入匹配到 MCP 服务器的工具。
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .client import MCPClient


logger = logging.getLogger(__name__)


@dataclass
class ToolInfo:
    """工具信息"""
    server_name: str
    tool_name: str
    description: str
    keywords: List[str]


@dataclass
class MatchResult:
    """匹配结果"""
    server_name: str
    tool_name: str
    arguments: Dict[str, Any]
    confidence: float
    keywords_matched: List[str]


class ToolMatcher:
    """
    MCP 工具意图匹配器

    使用关键词匹配将用户输入路由到合适的 MCP 工具。
    """

    def __init__(self, mcp_client: MCPClient):
        """
        初始化工具匹配器

        Args:
            mcp_client: MCP 客户端
        """
        self._client = mcp_client
        self._tool_index: Dict[str, List[ToolInfo]] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """初始化工具索引"""
        if self._initialized:
            return

        servers = self._client.list_servers()

        for server_name in servers:
            try:
                tools = await self._client.list_tools(server_name)

                for tool in tools:
                    tool_info = ToolInfo(
                        server_name=server_name,
                        tool_name=tool.get("name", ""),
                        description=tool.get("description", ""),
                        keywords=self._extract_keywords(tool)
                    )

                    if server_name not in self._tool_index:
                        self._tool_index[server_name] = []

                    self._tool_index[server_name].append(tool_info)
                    logger.debug(
                        f"索引工具: {server_name}/{tool_info.tool_name}, "
                        f"关键词: {tool_info.keywords}"
                    )

            except Exception as e:
                logger.warning(f"获取服务器 {server_name} 工具列表失败: {e}")

        self._initialized = True
        logger.info(f"工具匹配器初始化完成: {sum(len(v) for v in self._tool_index.values())} 个工具")

    def _extract_keywords(self, tool: Dict[str, Any]) -> List[str]:
        """
        从工具定义中提取关键词

        Args:
            tool: 工具定义

        Returns:
            List[str]: 关键词列表
        """
        keywords = []

        # 从描述中提取关键词
        description = tool.get("description", "").lower()
        name = tool.get("name", "").lower()

        # 常见操作关键词
        action_keywords = {
            "read": ["read", "读取", "查看", "获取", "get", "fetch", "显示"],
            "write": ["write", "写入", "保存", "save", "创建", "create"],
            "delete": ["delete", "删除", "remove", "移除"],
            "search": ["search", "搜索", "查找", "find", "query"],
            "list": ["list", "列出", "枚举", "enumerate"],
            "execute": ["execute", "执行", "run", "运行"],
        }

        # 匹配操作关键词
        for action, words in action_keywords.items():
            if action in name or any(w in description for w in words):
                keywords.extend(words)

        # 从名称中提取关键词（按驼峰或下划线分割）
        name_parts = name.replace("_", " ").replace("-", " ").split()
        keywords.extend([p for p in name_parts if len(p) > 2])

        # 去重并返回
        return list(set(keywords))

    async def match(self, user_input: str) -> Optional[MatchResult]:
        """
        匹配用户输入到 MCP 工具

        Args:
            user_input: 用户输入

        Returns:
            Optional[MatchResult]: 匹配结果，None 表示未匹配
        """
        if not self._initialized:
            await self.initialize()

        if not self._tool_index:
            return None

        user_input_lower = user_input.lower()
        best_match: Optional[MatchResult] = None
        best_score = 0.0

        # 遍历所有工具
        for server_name, tools in self._tool_index.items():
            for tool_info in tools:
                # 计算匹配分数
                score, matched_keywords = self._calculate_score(
                    user_input_lower, tool_info
                )

                # 置信度阈值
                if score > best_score and score >= 0.5:
                    best_score = score
                    best_match = MatchResult(
                        server_name=server_name,
                        tool_name=tool_info.tool_name,
                        arguments=self._build_arguments(user_input, tool_info),
                        confidence=score,
                        keywords_matched=matched_keywords
                    )

        if best_match:
            logger.info(
                f"MCP 工具匹配: {best_match.server_name}/{best_match.tool_name}, "
                f"置信度={best_match.confidence:.2f}"
            )

        return best_match

    def _calculate_score(
        self,
        user_input: str,
        tool_info: ToolInfo
    ) -> tuple[float, List[str]]:
        """
        计算匹配分数

        Args:
            user_input: 用户输入（小写）
            tool_info: 工具信息

        Returns:
            tuple[float, List[str]]: (分数, 匹配的关键词)
        """
        matched_keywords = []
        score = 0.0

        for keyword in tool_info.keywords:
            if keyword in user_input:
                score += 0.3
                matched_keywords.append(keyword)

        # 工具名称直接匹配加分
        if tool_info.tool_name in user_input:
            score += 0.5

        # 归一化分数到 0-1
        score = min(score, 1.0)

        return score, matched_keywords

    def _build_arguments(self, user_input: str, tool_info: ToolInfo) -> Dict[str, Any]:
        """
        构建工具调用参数

        Args:
            user_input: 用户输入
            tool_info: 工具信息

        Returns:
            Dict[str, Any]: 参数字典
        """
        # 这里是简化实现，实际需要根据工具的 inputSchema 构建参数
        # 可以使用 LLM 来解析用户输入并构建参数

        # 简单启发式：尝试从用户输入中提取参数
        args = {}

        # 对于文件操作，尝试提取路径
        if "file" in tool_info.tool_name.lower() or "read" in tool_info.tool_name.lower():
            # 查找可能的文件路径
            words = user_input.split()
            for word in words:
                if "." in word or "/" in word or "\\" in word:
                    args["path"] = word.strip('"\'')
                    break

        # 对于搜索操作，使用整个输入作为查询
        if "search" in tool_info.tool_name.lower() or "query" in tool_info.tool_name.lower():
            args["query"] = user_input

        return args

    def list_tools(self) -> Dict[str, List[str]]:
        """
        列出所有已索引的工具

        Returns:
            Dict[str, List[str]]: {server_name: [tool_names]}
        """
        return {
            server_name: [t.tool_name for t in tools]
            for server_name, tools in self._tool_index.items()
        }
