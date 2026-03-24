"""
Skill 注册器

扫描 skills 目录，将 skills 注册到 ToolRegistry。
"""

import asyncio
import importlib.util
import logging
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .tool_registry import ToolRegistry, get_global_registry
from .tool import Tool, ToolType, ToolParameter, ToolResult


logger = logging.getLogger(__name__)


def parse_skill_md(skill_md_path: Path) -> Dict[str, Any]:
    """
    解析 SKILL.md 文件，提取元数据

    Args:
        skill_md_path: SKILL.md 文件路径

    Returns:
        Dict: 技能元数据
    """
    content = skill_md_path.read_text(encoding="utf-8")

    metadata = {
        "name": skill_md_path.parent.name,
        "description": "",
        "version": "1.0.0",
        "keywords": [],
        "examples": [],
    }

    # 解析 YAML frontmatter
    in_frontmatter = False
    frontmatter_lines = []

    for line in content.split("\n"):
        if line.strip() == "---":
            if in_frontmatter:
                break
            in_frontmatter = True
            continue

        if in_frontmatter:
            frontmatter_lines.append(line)
            continue

    # 解析 frontmatter
    for line in frontmatter_lines:
        if line.startswith("name:"):
            metadata["name"] = line.split(":", 1)[1].strip()
        elif line.startswith("description:"):
            metadata["description"] = line.split(":", 1)[1].strip()
        elif line.startswith("version:"):
            metadata["version"] = line.split(":", 1)[1].strip()
        elif line.startswith("keywords:"):
            # 解析列表格式
            keywords_str = line.split(":", 1)[1].strip()
            if keywords_str.startswith("["):
                # [item1, item2] 格式
                keywords_str = keywords_str.strip("[]")
                metadata["keywords"] = [k.strip().strip("\"'") for k in keywords_str.split(",")]
        elif line.startswith("  - "):
            # YAML 列表项
            item = line.strip()[2:].strip()
            if "keywords" in metadata:
                metadata["keywords"].append(item)

    # 如果没有从 frontmatter 获取描述，尝试从标题获取
    if not metadata["description"]:
        for line in content.split("\n"):
            if line.startswith("# "):
                metadata["description"] = line[2:].strip()
                break

    return metadata


def load_skill_executor(skill_path: Path) -> Optional[Callable]:
    """
    加载 skill 的 executor.py

    Args:
        skill_path: Skill 目录路径

    Returns:
        Optional[Callable]: execute 函数，失败返回 None
    """
    executor_path = skill_path / "scripts" / "executor.py"
    if not executor_path.exists():
        logger.debug(f"Skill {skill_path.name} 没有 executor.py")
        return None

    try:
        spec = importlib.util.spec_from_file_location(
            f"skill.{skill_path.name}.executor",
            executor_path
        )
        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if hasattr(module, "execute"):
            return module.execute
        else:
            logger.warning(f"Skill {skill_path.name} 的 executor.py 没有 execute 函数")
            return None

    except Exception as e:
        logger.error(f"加载 Skill {skill_path.name} 的 executor 失败: {e}")
        return None


def create_skill_handler(skill_path: Path, execute_func: Callable) -> Callable:
    """
    为 skill 创建异步 handler

    Args:
        skill_path: Skill 目录路径
        execute_func: executor.py 中的 execute 函数

    Returns:
        Callable: 异步 handler 函数
    """
    async def handler(**kwargs) -> ToolResult:
        """Skill 执行 handler"""
        try:
            # 构建上下文
            context = {
                "skill_path": str(skill_path),
                "session_id": kwargs.get("session_id", "default"),
            }

            # 调用 executor
            if asyncio.iscoroutinefunction(execute_func):
                result = await execute_func(context, kwargs)
            else:
                result = execute_func(context, kwargs)

            # 统一返回格式
            if isinstance(result, ToolResult):
                return result
            elif isinstance(result, dict):
                return ToolResult(
                    success=result.get("success", True),
                    data=result.get("data") or result.get("response"),
                    error=result.get("error"),
                )
            else:
                return ToolResult(success=True, data=result)

        except Exception as e:
            logger.error(f"Skill 执行失败 [{skill_path.name}]: {e}")
            return ToolResult(success=False, error=str(e))

    return handler


def register_skills_to_registry(
    skills_dir: str = "skills",
    registry: Optional[ToolRegistry] = None
) -> List[str]:
    """
    扫描 skills 目录并注册到 ToolRegistry

    Args:
        skills_dir: Skills 目录路径
        registry: ToolRegistry 实例（默认使用全局实例）

    Returns:
        List[str]: 已注册的 skill 名称列表
    """
    if registry is None:
        registry = get_global_registry()

    skills_path = Path(skills_dir)
    if not skills_path.exists():
        logger.warning(f"Skills 目录不存在: {skills_path}")
        return []

    registered = []

    for skill_path in skills_path.iterdir():
        if not skill_path.is_dir():
            continue

        # 跳过模板目录
        if skill_path.name.startswith("_"):
            continue

        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            logger.debug(f"Skill {skill_path.name} 没有 SKILL.md，跳过")
            continue

        try:
            # 解析元数据
            metadata = parse_skill_md(skill_md)

            # 加载 executor
            execute_func = load_skill_executor(skill_path)
            handler = None
            if execute_func:
                handler = create_skill_handler(skill_path, execute_func)

            # 创建 Tool
            tool = Tool(
                name=f"skill.{metadata['name']}",
                type=ToolType.SKILL,
                description=metadata["description"],
                handler=handler,
                parameters=[
                    ToolParameter(
                        name="query",
                        type="string",
                        description="用户查询内容",
                        required=True
                    )
                ],
                metadata={
                    "skill_name": metadata["name"],
                    "version": metadata["version"],
                    "keywords": metadata.get("keywords", []),
                    "skill_path": str(skill_path)
                }
            )

            # 注册到 registry
            registry.register_tool(tool)
            registered.append(metadata["name"])
            logger.info(f"已注册 Skill: {metadata['name']} - {metadata['description']}")

        except Exception as e:
            logger.error(f"注册 Skill {skill_path.name} 失败: {e}")

    return registered


async def load_and_register_skills(
    skills_dir: str = "skills",
    registry: Optional[ToolRegistry] = None
) -> List[str]:
    """
    异步加载并注册 skills（兼容异步调用）

    Args:
        skills_dir: Skills 目录路径
        registry: ToolRegistry 实例

    Returns:
        List[str]: 已注册的 skill 名称列表
    """
    return register_skills_to_registry(skills_dir, registry)
