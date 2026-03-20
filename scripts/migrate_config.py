#!/usr/bin/env python3
"""
配置迁移脚本

将 .claude/ 目录中的配置迁移到 register/ 目录。

使用方式：
    python scripts/migrate_config.py          # 执行迁移（会备份）
    python scripts/migrate_config.py --dry-run  # 模拟执行
    python scripts/migrate_config.py --no-backup  # 不备份直接迁移
    python scripts/migrate_config.py --validate  # 验证迁移结果
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.migrator import ConfigMigrator, should_migrate
from src.config.loader import ConfigLoader


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="配置迁移工具")
    parser.add_argument("--dry-run", action="store_true", help="模拟执行，不实际修改文件")
    parser.add_argument("--no-backup", action="store_true", help="不备份原配置")
    parser.add_argument("--validate", action="store_true", help="验证迁移结果")
    parser.add_argument("--check", action="store_true", help="检查是否需要迁移")
    parser.add_argument("--project-root", default=".", help="项目根目录")

    args = parser.parse_args()

    if args.check:
        # 检查是否需要迁移
        need_migrate, reasons = should_migrate(args.project_root)
        if need_migrate:
            print("检测到需要迁移配置：")
            for reason in reasons:
                print(f"  - {reason}")
            print("\n建议运行: python scripts/migrate_config.py")
            return 1
        else:
            print("配置已是最新格式，无需迁移。")
            return 0

    if args.validate:
        # 验证迁移结果
        migrator = ConfigMigrator(args.project_root)
        result = migrator.validate_migration()

        if result["valid"]:
            print("✓ 配置迁移验证通过")
            if result["warnings"]:
                print("\n警告:")
                for warning in result["warnings"]:
                    print(f"  - {warning}")
            return 0
        else:
            print("✗ 配置迁移验证失败")
            print("\n问题:")
            for issue in result["issues"]:
                print(f"  - {issue}")
            return 1

    # 执行迁移
    print("=" * 50)
    print("配置迁移工具")
    print("=" * 50)

    migrator = ConfigMigrator(args.project_root)

    # 显示当前配置来源
    loader = ConfigLoader(args.project_root)
    sources = loader.detect_config_sources()

    print("\n当前配置来源:")
    for config_type, paths in sources.items():
        print(f"  {config_type}:")
        for path in paths:
            print(f"    - {path}")

    # 执行迁移
    result = migrator.migrate(
        backup=not args.no_backup,
        dry_run=args.dry_run,
    )

    print("\n" + "=" * 50)
    print("迁移结果")
    print("=" * 50)

    if args.dry_run:
        print("[DRY RUN] 模拟执行，未实际修改文件")

    if result["backup_path"]:
        print(f"✓ 配置已备份到: {result['backup_path']}")

    if result["migrated"]:
        print("\n已迁移:")
        for item in result["migrated"]:
            print(f"  ✓ {item}")

    if result["skipped"]:
        print("\n已跳过:")
        for item in result["skipped"]:
            print(f"  - {item}")

    if result["errors"]:
        print("\n错误:")
        for error in result["errors"]:
            print(f"  ✗ {error}")
        return 1

    print("\n迁移完成！")
    return 0


if __name__ == "__main__":
    sys.exit(main())
