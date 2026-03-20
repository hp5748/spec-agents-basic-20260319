# 任务卡

## 基本信息
- **任务ID**: T009
- **标题**: 配置兼容层实现
- **负责角色**: developer
- **优先级**: P0
- **状态**: pending
- **创建时间**: 2026-03-20
- **依赖**: T001

## 背景说明

### 问题描述
需要同时支持 `.claude/` 和 `register/` 两种配置目录，确保向后兼容。

### 核心目标
自动检测并加载两种配置格式，平滑过渡。

## 任务描述

实现配置兼容层，包括：

1. **配置加载器**
   - 扫描 `.claude/` 目录
   - 扫描 `register/` 目录
   - 合并配置（后者覆盖前者）

2. **配置文件支持**
   - `.claude/mcp.json` / `register/mcp.json`
   - `.claude/agents.json` / `register/agents.json`
   - `.claude/skills.json` / `register/skills.json`

3. **自动迁移**
   - 检测到旧配置时提示迁移
   - 提供迁移工具脚本

4. **配置验证**
   - Schema 验证
   - 冲突检测
   - 友好错误提示

## 技术约束

- JSON Schema 验证
- 支持配置热加载（可选）
- 向后兼容优先

## 验收标准
- [ ] 能正确加载两种配置格式
- [ ] 配置合并逻辑正确
- [ ] 迁移工具可用
- [ ] 错误提示友好

## 输出产物
- [ ] 产物1: `src/config/loader.py` - 配置加载器
- [ ] 产物2: `src/config/migrator.py` - 配置迁移工具
- [ ] 产物3: `scripts/migrate_config.py` - 迁移脚本
- [ ] 产物4: `tests/test_config_loader.py` - 单元测试
