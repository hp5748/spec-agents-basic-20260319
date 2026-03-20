"""
Skill 执行器

动态加载并执行 Skill 的 executor.py。
"""

import importlib.util
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .skill_loader import SkillLoader


logger = logging.getLogger(__name__)


@dataclass
class SkillContext:
    """Skill 执行上下文"""
    session_id: str
    user_input: str
    intent: str = ""
    chat_history: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillResult:
    """Skill 执行结果"""
    success: bool
    response: str
    data: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    # 调用链追踪字段
    source_type: str = "skill"  # "skill", "subagent", "mcp", "llm"
    source_name: str = ""       # 具体模块名称
    chain_info: List[str] = field(default_factory=list)  # 完整调用链


class SkillExecutor:
    """
    Skill 执行器

    动态加载 Skill 目录下的 executor.py 并执行。

    使用方式：
        executor = SkillExecutor("skills")
        context = SkillContext(
            session_id="test",
            user_input="查询张三",
            intent="person_search"
        )
        result = await executor.execute("sqlite-query-skill", context)
        print(result.response)
    """

    def __init__(self, skills_dir: str = "skills"):
        """
        初始化执行器

        Args:
            skills_dir: Skill 根目录
        """
        self._skills_dir = Path(skills_dir)
        self._loader = SkillLoader(skills_dir)
        self._executor_cache: Dict[str, Callable] = {}

    async def execute(
        self,
        skill_name: str,
        context: SkillContext
    ) -> SkillResult:
        """
        执行指定 Skill

        Args:
            skill_name: Skill 名称
            context: 执行上下文

        Returns:
            SkillResult: 执行结果
        """
        # 获取执行函数
        executor_func = self._get_executor(skill_name)
        if not executor_func:
            return SkillResult(
                success=False,
                response="",
                error=f"Skill '{skill_name}' 不存在或没有 executor.py"
            )

        try:
            # 准备输入数据
            input_data = {
                "user_input": context.user_input,
                "intent": context.intent,
                "chat_history": context.chat_history,
                **context.metadata
            }

            # 调用执行器
            # executor.py 的 execute 函数签名: execute(context: dict, input_data: dict) -> dict
            result = executor_func(
                {"session_id": context.session_id},
                input_data
            )

            # 解析结果
            if isinstance(result, dict):
                return SkillResult(
                    success=result.get("success", True),
                    response=result.get("response", ""),
                    data=result.get("data", {}),
                    error=result.get("error", "")
                )
            else:
                return SkillResult(
                    success=True,
                    response=str(result),
                    data={}
                )

        except Exception as e:
            logger.error(f"Skill 执行失败 [{skill_name}]: {e}")
            return SkillResult(
                success=False,
                response="",
                error=f"执行错误: {str(e)}"
            )

    def _get_executor(self, skill_name: str) -> Optional[Callable]:
        """
        获取 Skill 的执行函数（带缓存）

        Args:
            skill_name: Skill 名称

        Returns:
            Optional[Callable]: 执行函数
        """
        # 检查缓存
        if skill_name in self._executor_cache:
            return self._executor_cache[skill_name]

        # 查找 executor.py
        executor_path = self._skills_dir / skill_name / "scripts" / "executor.py"
        if not executor_path.exists():
            logger.warning(f"未找到 executor.py: {executor_path}")
            return None

        # 动态加载模块
        try:
            spec = importlib.util.spec_from_file_location(
                f"skills.{skill_name}.executor",
                executor_path
            )
            if not spec or not spec.loader:
                return None

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 获取 execute 函数
            if hasattr(module, "execute"):
                executor_func = module.execute
                self._executor_cache[skill_name] = executor_func
                logger.info(f"已加载 Skill 执行器: {skill_name}")
                return executor_func
            else:
                logger.warning(f"executor.py 没有 execute 函数: {skill_name}")
                return None

        except Exception as e:
            logger.error(f"加载 executor.py 失败 [{skill_name}]: {e}")
            return None

    def clear_cache(self) -> None:
        """清空执行器缓存"""
        self._executor_cache.clear()
        logger.info("执行器缓存已清空")

    def reload_skill(self, skill_name: str) -> bool:
        """
        重新加载指定 Skill

        Args:
            skill_name: Skill 名称

        Returns:
            bool: 是否成功
        """
        if skill_name in self._executor_cache:
            del self._executor_cache[skill_name]

        executor = self._get_executor(skill_name)
        return executor is not None
