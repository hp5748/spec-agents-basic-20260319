"""
Skills 加载器

扫描 skills/ 目录，加载技能配置和处理器，注册到 ToolRegistry。
"""

import asyncio
import importlib
import importlib.util
import inspect
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .executor import PythonAdapter, get_python_adapter


logger = logging.getLogger(__name__)


class SkillMetadata:
    """技能元数据"""

    def __init__(
        self,
        name: str,
        description: str,
        version: str = "1.0.0",
        author: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.description = description
        self.version = version
        self.author = author
        self.parameters = parameters or {}


class SkillLoader:
    """
    Skills 加载器

    扫描 skills/ 目录，加载技能配置和处理器。
    """

    def __init__(
        self,
        skills_dir: str = "skills",
        adapter: Optional[PythonAdapter] = None,
    ):
        self.skills_dir = Path(skills_dir)
        self.adapter = adapter or get_python_adapter()
        self._loaded_skills: Dict[str, SkillMetadata] = {}

    async def load_all(self) -> Dict[str, SkillMetadata]:
        """加载所有技能"""
        if not self.skills_dir.exists():
            logger.warning(f"Skills 目录不存在: {self.skills_dir}")
            return {}

        logger.info(f"开始扫描 skills 目录: {self.skills_dir}")

        # 扫描所有子目录
        for skill_path in self.skills_dir.iterdir():
            if skill_path.is_dir() and not skill_path.name.startswith("_"):
                await self._load_skill(skill_path)

        logger.info(f"加载完成，共加载 {len(self._loaded_skills)} 个技能")
        return self._loaded_skills

    async def _load_skill(self, skill_path: Path) -> Optional[SkillMetadata]:
        """加载单个技能"""
        skill_name = skill_path.name

        try:
            # 读取元数据文件
            metadata = self._load_metadata(skill_path)

            # 加载处理器
            await self._load_handler(skill_path, metadata)

            self._loaded_skills[skill_name] = metadata
            logger.info(f"加载技能: {skill_name} - {metadata.description}")
            return metadata

        except Exception as e:
            logger.error(f"加载技能 {skill_name} 失败: {e}")
            return None

    def _load_metadata(self, skill_path: Path) -> SkillMetadata:
        """加载技能元数据"""
        # 尝试读取 SKILL.md
        skill_md = skill_path / "SKILL.md"
        if skill_md.exists():
            return self._parse_skill_md(skill_md)

        # 尝试读取 skill.json
        skill_json = skill_path / "skill.json"
        if skill_json.exists():
            return self._parse_skill_json(skill_json)

        # 使用默认元数据
        return SkillMetadata(
            name=skill_path.name,
            description=f"技能: {skill_path.name}",
        )

    def _parse_skill_md(self, skill_md: Path) -> SkillMetadata:
        """解析 SKILL.md"""
        content = skill_md.read_text(encoding="utf-8")

        # 简单解析（实际应使用更完善的 Markdown 解析）
        name = skill_md.parent.name
        description = "未找到描述"
        version = "1.0.0"
        author = None

        for line in content.split("\n"):
            if line.startswith("# "):
                description = line[2:].strip()
            elif line.startswith("**版本**:") or line.startswith("版本:"):
                version = line.split(":")[-1].strip()
            elif line.startswith("**作者**:") or line.startswith("作者:"):
                author = line.split(":")[-1].strip()

        return SkillMetadata(
            name=name,
            description=description,
            version=version,
            author=author,
        )

    def _parse_skill_json(self, skill_json: Path) -> SkillMetadata:
        """解析 skill.json"""
        import json

        data = json.loads(skill_json.read_text(encoding="utf-8"))
        return SkillMetadata(
            name=data.get("name", skill_json.parent.name),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            author=data.get("author"),
            parameters=data.get("parameters"),
        )

    async def _load_handler(self, skill_path: Path, metadata: SkillMetadata) -> None:
        """加载技能处理器"""
        # 查找 handler.py
        handler_py = skill_path / "handler.py"
        if not handler_py.exists():
            logger.debug(f"技能 {skill_path.name} 没有 handler.py，跳过")
            return

        # 动态导入模块
        try:
            spec = importlib.util.spec_from_file_location(
                f"skill.{skill_path.name}",
                handler_py,
            )
            if spec is None or spec.loader is None:
                logger.error(f"无法加载模块: {handler_py}")
                return

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 查找 execute 函数
            if hasattr(module, "execute"):
                self.adapter.register_function(
                    name=skill_path.name,
                    func=module.execute,
                    description=metadata.description,
                    metadata={"skill_path": str(skill_path)},
                )

            # 查找 Schema 函数
            if hasattr(module, "get_schema"):
                schema = module.get_schema()
                # 可以使用 schema 更新参数定义

        except Exception as e:
            logger.error(f"加载处理器失败 {handler_py}: {e}")

    def get_loaded_skills(self) -> Dict[str, SkillMetadata]:
        """获取已加载的技能"""
        return self._loaded_skills.copy()

    def get_skill(self, name: str) -> Optional[SkillMetadata]:
        """获取指定技能"""
        return self._loaded_skills.get(name)


async def load_skills(
    skills_dir: str = "skills",
    adapter: Optional[PythonAdapter] = None,
) -> Dict[str, SkillMetadata]:
    """
    便捷函数：加载所有技能

    Args:
        skills_dir: Skills 目录路径
        adapter: Python 适配器

    Returns:
        技能元数据字典
    """
    loader = SkillLoader(skills_dir, adapter)
    return await loader.load_all()
