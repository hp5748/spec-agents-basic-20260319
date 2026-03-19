"""
意图识别器

基于关键词匹配识别用户意图，返回最佳匹配的 Skill。
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..skill_loader import SkillLoader


logger = logging.getLogger(__name__)


@dataclass
class IntentResult:
    """意图识别结果"""
    skill_name: Optional[str] = None      # 匹配的 Skill 名称
    confidence: float = 0.0                # 置信度 0.0-1.0
    matched_keywords: List[str] = field(default_factory=list)  # 匹配的关键词
    matched_intents: List[str] = field(default_factory=list)   # 匹配的意图


class IntentRecognizer:
    """
    意图识别器

    基于关键词匹配识别用户意图。

    使用方式：
        recognizer = IntentRecognizer("skills")
        result = recognizer.recognize("查询张三的信息")
        if result.skill_name:
            print(f"匹配到 Skill: {result.skill_name}")
    """

    def __init__(self, skills_dir: str = "skills"):
        """
        初始化意图识别器

        Args:
            skills_dir: Skill 根目录
        """
        self._skills_dir = skills_dir
        self._loader = SkillLoader(skills_dir)
        self._skills: Dict[str, Dict[str, Any]] = {}
        self._load_all_skills()

    def _load_all_skills(self) -> None:
        """加载所有 Skill 的元数据"""
        skill_names = self._loader.list_skills()
        for skill_name in skill_names:
            metadata = self._loader.load_skill(skill_name)
            if metadata:
                self._skills[skill_name] = metadata
                logger.debug(f"加载 Skill 元数据: {skill_name}")

        logger.info(f"意图识别器已加载 {len(self._skills)} 个 Skill")

    def recognize(self, user_input: str) -> IntentResult:
        """
        识别用户意图

        策略：
        1. 关键词匹配（快速）
        2. 返回置信度最高的 Skill

        Args:
            user_input: 用户输入

        Returns:
            IntentResult: 意图识别结果
        """
        if not user_input or not self._skills:
            return IntentResult()

        user_input_lower = user_input.lower()
        best_match: Optional[str] = None
        best_score = 0.0
        matched_keywords: List[str] = []
        matched_intents: List[str] = []

        for skill_name, metadata in self._skills.items():
            keywords = metadata.get("keywords", [])
            if not keywords:
                continue

            # 计算匹配分数
            score = 0.0
            skill_matched_keywords = []

            for kw in keywords:
                if kw.lower() in user_input_lower:
                    # 关键词权重：匹配一个关键词得 1 分
                    score += 1.0
                    skill_matched_keywords.append(kw)

            if score > best_score:
                best_score = score
                best_match = skill_name
                matched_keywords = skill_matched_keywords
                # 获取意图列表
                matched_intents = metadata.get("intents", [])

        # 计算置信度（归一化到 0-1）
        confidence = min(best_score, 1.0) if best_match else 0.0

        # 置信度阈值过滤
        if confidence < 0.1:
            return IntentResult()

        result = IntentResult(
            skill_name=best_match,
            confidence=confidence,
            matched_keywords=matched_keywords,
            matched_intents=matched_intents
        )

        if best_match:
            logger.info(
                f"意图识别: skill={best_match}, "
                f"confidence={confidence:.2f}, "
                f"keywords={matched_keywords}"
            )

        return result

    def reload(self) -> int:
        """
        重新加载所有 Skill

        Returns:
            int: 加载的 Skill 数量
        """
        self._skills.clear()
        self._load_all_skills()
        return len(self._skills)

    def list_skills(self) -> List[str]:
        """列出所有已加载的 Skill"""
        return list(self._skills.keys())

    def get_skill_metadata(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """获取指定 Skill 的元数据"""
        return self._skills.get(skill_name)
