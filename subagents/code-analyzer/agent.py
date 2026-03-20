"""
代码分析 Agent

专门负责代码分析、问题检测和模式识别。
"""

import re
from typing import Dict, Any
from src.subagent import SubAgent, SubAgentInput, SubAgentOutput, AgentConfig


class Agent(SubAgent):
    """
    代码分析 Agent

    专注于代码质量分析、问题检测和最佳实践建议。
    """

    def __init__(self, agent_id: str, config: AgentConfig, llm_client=None):
        super().__init__(agent_id, config, llm_client)
        self.set_system_prompt(
            "你是一个代码分析专家，能够检测代码问题、"
            "识别反模式并提供改进建议。"
        )

    async def process(self, input_data: SubAgentInput) -> SubAgentOutput:
        """处理代码分析请求"""
        try:
            code = input_data.query
            analysis = self._analyze_code(code)

            return SubAgentOutput(
                success=True,
                response=self._format_analysis(analysis),
                data=analysis
            )
        except Exception as e:
            return SubAgentOutput(
                success=False,
                response="代码分析失败",
                error=str(e)
            )

    def can_handle(self, input_data: SubAgentInput) -> float:
        """判断是否为代码分析请求"""
        keywords = ["分析", "检查", "review", "analyze", "代码", "code"]
        query_lower = input_data.query.lower()

        for kw in keywords:
            if kw in query_lower:
                return 0.8

        # 检查是否包含代码特征
        if re.search(r'[{}();]', input_data.query):
            return 0.5

        return 0.0

    def _analyze_code(self, code: str) -> Dict[str, Any]:
        """分析代码"""
        issues = []
        suggestions = []

        # 简单的代码模式检测
        if "TODO" in code or "FIXME" in code:
            issues.append("代码中包含 TODO/FIXME 标记")

        if len(code.splitlines()) > 100:
            suggestions.append("代码较长，建议拆分为更小的函数")

        if "print(" in code and "def " not in code:
            suggestions.append("建议将代码封装为函数")

        # 检测常见反模式
        if code.count("except:") > 0:
            issues.append("使用了空的 except 子句，可能隐藏错误")

        return {
            "issues": issues,
            "suggestions": suggestions,
            "line_count": len(code.splitlines()),
            "char_count": len(code)
        }

    def _format_analysis(self, analysis: Dict[str, Any]) -> str:
        """格式化分析结果"""
        parts = ["## 代码分析结果\n"]

        if analysis["issues"]:
            parts.append("### 发现的问题")
            for issue in analysis["issues"]:
                parts.append(f"- ⚠️ {issue}")
            parts.append("")

        if analysis["suggestions"]:
            parts.append("### 改进建议")
            for suggestion in analysis["suggestions"]:
                parts.append(f"- 💡 {suggestion}")
            parts.append("")

        parts.append(f"### 统计信息")
        parts.append(f"- 行数: {analysis['line_count']}")
        parts.append(f"- 字符数: {analysis['char_count']}")

        return "\n".join(parts)
