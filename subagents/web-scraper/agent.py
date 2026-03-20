"""
网页抓取 Agent

负责网页内容提取和基础数据处理。
"""

import re
from typing import Dict, Any
from src.subagent import SubAgent, SubAgentInput, SubAgentOutput, AgentConfig


class Agent(SubAgent):
    """
    网页抓取 Agent

    提供网页内容提取、URL 解析和基础数据处理功能。
    """

    def __init__(self, agent_id: str, config: AgentConfig, llm_client=None):
        super().__init__(agent_id, config, llm_client)
        self.set_system_prompt(
            "你是一个网页数据提取专家，能够从网页内容中提取结构化信息。"
        )

    async def process(self, input_data: SubAgentInput) -> SubAgentOutput:
        """处理网页抓取请求"""
        try:
            query = input_data.query
            result = self._process_web_request(query)

            return SubAgentOutput(
                success=True,
                response=self._format_result(result),
                data=result
            )
        except Exception as e:
            return SubAgentOutput(
                success=False,
                response="网页处理失败",
                error=str(e)
            )

    def can_handle(self, input_data: SubAgentInput) -> float:
        """判断是否为网页相关请求"""
        keywords = [
            "抓取", "爬取", "网页", "网站", "url", "http",
            "scrape", "crawl", "web", "website", "extract"
        ]
        query_lower = input_data.query.lower()

        for kw in keywords:
            if kw in query_lower:
                return 0.8

        # 检测 URL
        if re.search(r'https?://', input_data.query):
            return 0.9

        return 0.0

    def _process_web_request(self, query: str) -> Dict[str, Any]:
        """处理网页请求"""
        result = {
            "urls": self._extract_urls(query),
            "emails": self._extract_emails(query),
            "phones": self._extract_phones(query),
        }

        # 统计信息
        result["url_count"] = len(result["urls"])
        result["email_count"] = len(result["emails"])
        result["phone_count"] = len(result["phones"])

        return result

    def _extract_urls(self, text: str) -> list:
        """提取 URL"""
        pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        return re.findall(pattern, text)

    def _extract_emails(self, text: str) -> list:
        """提取邮箱"""
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        return re.findall(pattern, text)

    def _extract_phones(self, text: str) -> list:
        """提取手机号"""
        pattern = r'1[3-9]\d{9}'
        return re.findall(pattern, text)

    def _format_result(self, result: Dict[str, Any]) -> str:
        """格式化结果"""
        parts = ["## 网页数据提取结果\n"]

        if result["urls"]:
            parts.append("### 发现的 URL")
            for url in result["urls"][:5]:  # 最多显示5个
                parts.append(f"- {url}")
            if len(result["urls"]) > 5:
                parts.append(f"- ... 还有 {len(result['urls']) - 5} 个")
            parts.append("")

        if result["emails"]:
            parts.append("### 发现的邮箱")
            for email in result["emails"][:5]:
                parts.append(f"- {email}")
            if len(result["emails"]) > 5:
                parts.append(f"- ... 还有 {len(result['emails']) - 5} 个")
            parts.append("")

        if result["phones"]:
            parts.append("### 发现的手机号")
            for phone in result["phones"][:5]:
                parts.append(f"- {phone}")
            if len(result["phones"]) > 5:
                parts.append(f"- ... 还有 {len(result['phones']) - 5} 个")
            parts.append("")

        parts.append("### 统计")
        parts.append(f"- URL: {result['url_count']} 个")
        parts.append(f"- 邮箱: {result['email_count']} 个")
        parts.append(f"- 手机号: {result['phone_count']} 个")

        return "\n".join(parts)
