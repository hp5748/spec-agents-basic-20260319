"""
配置迁移工具

将 .claude/ 目录中的配置迁移到 register/ 目录。
"""

import json
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from .loader import ConfigLoader


logger = logging.getLogger(__name__)


class ConfigMigrator:
    """
    配置迁移器

    将旧格式配置迁移到新格式：
    - .claude/mcp.json → register/mcp.json
    - .claude/agents.json → register/agents.json
    - .claude/skills.json → register/skills.json
    """

    def __init__(
        self,
        project_root: Optional[str] = None,
        claude_dir: str = ".claude",
        register_dir: str = "register",
    ):
        self.loader = ConfigLoader(project_root, claude_dir, register_dir)
        self.register_dir = Path(project_root or ".") / register_dir

    def migrate(
        self,
        backup: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, any]:
        """
        执行迁移

        Args:
            backup: 是否备份原配置
            dry_run: 是否只模拟执行

        Returns:
            迁移结果
        """
        result = {
            "success": True,
            "migrated": [],
            "skipped": [],
            "errors": [],
            "backup_path": None,
        }

        # 创建 register 目录
        if not dry_run and not self.register_dir.exists():
            self.register_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"创建目录: {self.register_dir}")

        # 备份
        if backup and not dry_run:
            backup_path = self._backup_configs()
            result["backup_path"] = str(backup_path)

        # 迁移配置文件
        migrations = [
            ("mcp.json", "mcp.json"),
            ("agents.json", "agents.json"),
            ("skills.json", "skills.json"),
        ]

        for source_file, target_file in migrations:
            try:
                if self._migrate_file(source_file, target_file, dry_run):
                    result["migrated"].append(f"{source_file} → {target_file}")
                else:
                    result["skipped"].append(source_file)
            except Exception as e:
                result["errors"].append(f"{source_file}: {str(e)}")
                logger.error(f"迁移失败 {source_file}: {e}")

        result["success"] = len(result["errors"]) == 0
        return result

    def _migrate_file(self, source_name: str, target_name: str, dry_run: bool) -> bool:
        """迁移单个文件"""
        source_path = self.loader.claude_dir / source_name
        target_path = self.register_dir / target_name

        if not source_path.exists():
            return False

        if dry_run:
            logger.info(f"[DRY RUN] 将迁移: {source_path} → {target_path}")
            return True

        # 读取源文件
        with open(source_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 写入目标文件
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"迁移完成: {source_path} → {target_path}")
        return True

    def _backup_configs(self) -> Path:
        """备份配置文件"""
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.loader.claude_dir / f"backup_{timestamp}"
        backup_dir.mkdir(exist_ok=True)

        # 备份所有 JSON 配置
        for json_file in self.loader.claude_dir.glob("*.json"):
            if json_file.name != ".claude.json":  # 跳过用户配置
                shutil.copy2(json_file, backup_dir / json_file.name)
                logger.info(f"备份: {json_file} → {backup_dir / json_file.name}")

        logger.info(f"配置已备份到: {backup_dir}")
        return backup_dir

    def rollback(self, backup_path: Optional[str] = None) -> bool:
        """
        回滚迁移

        Args:
            backup_path: 备份目录路径，默认使用最新备份

        Returns:
            是否成功回滚
        """
        if not backup_path:
            # 查找最新备份
            backups = sorted(
                self.loader.claude_dir.glob("backup_*"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if not backups:
                logger.error("未找到备份目录")
                return False
            backup_path = str(backups[0])

        backup_dir = Path(backup_path)
        if not backup_dir.exists():
            logger.error(f"备份目录不存在: {backup_dir}")
            return False

        # 恢复文件
        for json_file in backup_dir.glob("*.json"):
            target = self.loader.claude_dir / json_file.name
            shutil.copy2(json_file, target)
            logger.info(f"恢复: {json_file} → {target}")

        logger.info("配置已回滚")
        return True

    def validate_migration(self) -> Dict[str, any]:
        """验证迁移结果"""
        result = {
            "valid": True,
            "issues": [],
            "warnings": [],
        }

        # 检查 register 目录是否存在
        if not self.register_dir.exists():
            result["issues"].append("register/ 目录不存在")
            result["valid"] = False
            return result

        # 检查配置文件
        for config_name in ["mcp.json", "agents.json", "skills.json"]:
            config_path = self.register_dir / config_name
            if not config_path.exists():
                result["warnings"].append(f"{config_name} 不存在")
                continue

            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                result["issues"].append(f"{config_name} 格式错误: {e}")
                result["valid"] = False

        return result


def migrate_configs(
    project_root: Optional[str] = None,
    backup: bool = True,
    dry_run: bool = False,
) -> Dict[str, any]:
    """
    便捷函数：执行配置迁移

    Args:
        project_root: 项目根目录
        backup: 是否备份
        dry_run: 是否模拟执行

    Returns:
        迁移结果
    """
    migrator = ConfigMigrator(project_root=project_root)
    return migrator.migrate(backup=backup, dry_run=dry_run)


def should_migrate(project_root: Optional[str] = None) -> Tuple[bool, List[str]]:
    """便捷函数：检查是否需要迁移"""
    loader = ConfigLoader(project_root=project_root)
    return loader.should_migrate()
