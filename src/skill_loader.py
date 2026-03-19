"""
Skill 资源加载器

负责加载 Skill 目录下的各种资源文件。

支持的标准目录结构：
skill-name/
├── SKILL.md                  # 核心指令 + 元数据（必需）
├── templates/                # 常用模板
├── examples/                 # 优秀/反例
├── references/               # 规范、规则
└── scripts/                  # 可执行脚本

参考：
- alirezarezvani/claude-skills (192+ Skills)
- Claude Code Skills 规范
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path
import logging
import re
import yaml


logger = logging.getLogger(__name__)


@dataclass
class TemplateContent:
    """模板内容"""
    name: str
    path: str
    content: str
    description: str = ""


@dataclass
class ExampleContent:
    """示例内容"""
    name: str
    path: str
    content: str
    type: str = "good"  # good / anti-pattern
    description: str = ""


@dataclass
class ReferenceContent:
    """参考文档内容"""
    name: str
    path: str
    content: str
    category: str = ""  # rules / conventions / docs


@dataclass
class ScriptContent:
    """脚本内容"""
    name: str
    path: str
    content: str
    language: str = "python"  # python / shell / etc.


@dataclass
class SkillResources:
    """Skill 资源集合"""
    skill_name: str
    skill_path: str

    # 核心文件
    instruction: str = ""  # SKILL.md 正文内容（不含 YAML）
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 资源目录
    templates: List[TemplateContent] = field(default_factory=list)
    examples: List[ExampleContent] = field(default_factory=list)
    references: List[ReferenceContent] = field(default_factory=list)
    scripts: List[ScriptContent] = field(default_factory=list)

    # 加载状态
    loaded: bool = False
    errors: List[str] = field(default_factory=list)


class SkillLoader:
    """
    Skill 资源加载器

    负责从 Skill 目录加载所有资源文件。

    使用方式：
        loader = SkillLoader("skills")
        skills = loader.list_skills()
        resources = loader.load_skill("my-skill")
        print(resources.metadata)
        print(resources.templates)
    """

    # 支持的文件扩展名
    TEMPLATE_EXTENSIONS = {".md", ".txt", ".tsx.md", ".ts.md", ".py.md"}
    EXAMPLE_EXTENSIONS = {".md"}
    REFERENCE_EXTENSIONS = {".md", ".txt", ".yaml", ".json"}
    SCRIPT_EXTENSIONS = {".py", ".sh", ".bash", ".zsh"}

    def __init__(self, skills_dir: str = "skills", max_file_size: int = 100 * 1024):  # 100KB
        """
        初始化加载器

        Args:
            skills_dir: Skill 根目录
            max_file_size: 单文件最大大小（字节）
        """
        self.skills_dir = Path(skills_dir)
        self.max_file_size = max_file_size

    def list_skills(self) -> List[str]:
        """
        列出所有可用的 Skill

        Returns:
            List[str]: Skill 名称列表
        """
        skills = []
        if not self.skills_dir.exists():
            return skills

        for item in self.skills_dir.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                # 检查是否有 SKILL.md
                if (item / "SKILL.md").exists():
                    skills.append(item.name)

        return sorted(skills)

    def load_skill(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """
        加载指定 Skill 的配置

        Args:
            skill_name: Skill 名称

        Returns:
            Dict: Skill 配置（metadata）
        """
        skill_path = self.skills_dir / skill_name
        if not skill_path.exists():
            return None

        resources = self.load(str(skill_path))
        return resources.metadata if resources.loaded else None

    def load(self, skill_path: str) -> SkillResources:
        """
        加载 Skill 资源

        Args:
            skill_path: Skill 目录路径

        Returns:
            SkillResources: 资源集合
        """
        path = Path(skill_path)
        resources = SkillResources(
            skill_name=path.name,
            skill_path=str(path)
        )

        if not path.exists():
            resources.errors.append(f"Skill 目录不存在: {skill_path}")
            return resources

        # 1. 加载 SKILL.md
        self._load_skill_md(path, resources)

        # 2. 加载 templates/
        self._load_templates(path, resources)

        # 3. 加载 examples/
        self._load_examples(path, resources)

        # 4. 加载 references/
        self._load_references(path, resources)

        # 5. 加载 scripts/
        self._load_scripts(path, resources)

        resources.loaded = True
        return resources

    def _load_skill_md(self, path: Path, resources: SkillResources) -> None:
        """加载 SKILL.md 文件"""
        skill_md_path = path / "SKILL.md"

        if not skill_md_path.exists():
            resources.errors.append("SKILL.md 文件不存在")
            return

        try:
            content = skill_md_path.read_text(encoding="utf-8")

            # 解析 YAML Front Matter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    yaml_content = parts[1].strip()
                    resources.instruction = parts[2].strip()

                    try:
                        resources.metadata = yaml.safe_load(yaml_content) or {}
                    except yaml.YAMLError as e:
                        resources.errors.append(f"YAML 解析错误: {e}")
                        resources.metadata = {}
            else:
                resources.instruction = content

        except Exception as e:
            resources.errors.append(f"读取 SKILL.md 失败: {e}")

    def _load_templates(self, path: Path, resources: SkillResources) -> None:
        """加载 templates/ 目录"""
        templates_dir = path / "templates"

        if not templates_dir.exists():
            # 兼容旧的 assets/ 目录
            templates_dir = path / "assets"
            if not templates_dir.exists():
                return

        for file_path in templates_dir.rglob("*"):
            if file_path.is_file() and self._check_extension(file_path, self.TEMPLATE_EXTENSIONS):
                try:
                    content = self._read_file(file_path)
                    if content:
                        resources.templates.append(TemplateContent(
                            name=file_path.stem,
                            path=str(file_path.relative_to(path)),
                            content=content,
                            description=self._extract_description(content)
                        ))
                except Exception as e:
                    resources.errors.append(f"加载模板失败 {file_path}: {e}")

    def _load_examples(self, path: Path, resources: SkillResources) -> None:
        """加载 examples/ 目录"""
        examples_dir = path / "examples"

        if not examples_dir.exists():
            return

        for file_path in examples_dir.rglob("*"):
            if file_path.is_file() and self._check_extension(file_path, self.EXAMPLE_EXTENSIONS):
                try:
                    content = self._read_file(file_path)
                    if content:
                        # 根据文件名判断类型
                        file_name = file_path.stem.lower()
                        example_type = "anti-pattern" if "anti" in file_name or "bad" in file_name else "good"

                        resources.examples.append(ExampleContent(
                            name=file_path.stem,
                            path=str(file_path.relative_to(path)),
                            content=content,
                            type=example_type,
                            description=self._extract_description(content)
                        ))
                except Exception as e:
                    resources.errors.append(f"加载示例失败 {file_path}: {e}")

    def _load_references(self, path: Path, resources: SkillResources) -> None:
        """加载 references/ 目录"""
        references_dir = path / "references"

        if not references_dir.exists():
            return

        for file_path in references_dir.rglob("*"):
            if file_path.is_file() and self._check_extension(file_path, self.REFERENCE_EXTENSIONS):
                try:
                    content = self._read_file(file_path)
                    if content:
                        # 根据文件名判断类别
                        file_name = file_path.stem.lower()
                        if "rule" in file_name or "hook" in file_name:
                            category = "rules"
                        elif "convention" in file_name or "naming" in file_name:
                            category = "conventions"
                        else:
                            category = "docs"

                        resources.references.append(ReferenceContent(
                            name=file_path.stem,
                            path=str(file_path.relative_to(path)),
                            content=content,
                            category=category
                        ))
                except Exception as e:
                    resources.errors.append(f"加载参考文档失败 {file_path}: {e}")

    def _load_scripts(self, path: Path, resources: SkillResources) -> None:
        """加载 scripts/ 目录"""
        scripts_dir = path / "scripts"

        if not scripts_dir.exists():
            return

        for file_path in scripts_dir.rglob("*"):
            if file_path.is_file() and self._check_extension(file_path, self.SCRIPT_EXTENSIONS):
                try:
                    content = self._read_file(file_path)
                    if content:
                        # 根据扩展名判断语言
                        suffix = file_path.suffix.lower()
                        if suffix == ".py":
                            language = "python"
                        elif suffix in {".sh", ".bash"}:
                            language = "bash"
                        elif suffix == ".zsh":
                            language = "zsh"
                        else:
                            language = "unknown"

                        resources.scripts.append(ScriptContent(
                            name=file_path.stem,
                            path=str(file_path.relative_to(path)),
                            content=content,
                            language=language
                        ))
                except Exception as e:
                    resources.errors.append(f"加载脚本失败 {file_path}: {e}")

    def _read_file(self, file_path: Path) -> Optional[str]:
        """读取文件内容"""
        if file_path.stat().st_size > self.max_file_size:
            logger.warning(f"文件过大，跳过: {file_path}")
            return None

        return file_path.read_text(encoding="utf-8")

    def _check_extension(self, file_path: Path, extensions: set) -> bool:
        """检查文件扩展名"""
        # 处理复合扩展名如 .tsx.md
        name = file_path.name.lower()
        for ext in extensions:
            if name.endswith(ext):
                return True
        return file_path.suffix.lower() in extensions

    def _extract_description(self, content: str, max_lines: int = 5) -> str:
        """从内容中提取描述（前几行）"""
        lines = content.strip().split("\n")[:max_lines]
        # 过滤空行和 YAML 边界
        lines = [l for l in lines if l.strip() and not l.strip() == "---"]
        return " ".join(lines)[:200]  # 限制长度


def load_skill(skill_path: str) -> SkillResources:
    """
    快捷函数：加载 Skill 资源

    Args:
        skill_path: Skill 目录路径

    Returns:
        SkillResources: 资源集合
    """
    loader = SkillLoader()
    return loader.load(skill_path)
