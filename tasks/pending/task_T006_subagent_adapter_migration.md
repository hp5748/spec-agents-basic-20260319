# 任务卡

## 基本信息
- **任务ID**: T006
- **标题**: SubAgent Adapter 迁移
- **负责角色**: developer
- **优先级**: P0
- **状态**: pending
- **创建时间**: 2026-03-20
- **依赖**: T002, T004

## 背景说明

### 问题描述
将现有的 `src/subagent/` 模块迁移到 `src/adapters/subagent/`，并改造为符合新架构的 Adapter。

### 核心目标
保持 SubAgent 功能不变，同时适配新的 Adapter 接口。

## 任务描述

迁移并改造 SubAgent 模块，包括：

1. **目录迁移**
   - 移动 `src/subagent/` → `src/adapters/subagent/`
   - 更新所有 import 路径

2. **适配器改造**
   - 创建 `SubAgentAdapter` 继承 `BaseAdapter`
   - 实现新的 `execute()` 接口
   - 保持原有编排逻辑

3. **配置兼容**
   - 支持 `.claude/agents.json` 格式
   - 支持 `register/agents.json` 格式
   - 自动检测并加载

4. **上下文共享**
   - 集成 SharedState
   - 主子 Agent 上下文同步

## 技术约束

- 保持向后兼容
- 支持异步操作
- 上下文隔离与共享机制

## 验收标准
- [ ] 迁移后所有原有功能正常
- [ ] 符合 Adapter 接口规范
- [ ] 配置加载兼容两种格式
- [ ] 上下文共享机制生效

## 输出产物
- [ ] 产物1: `src/adapters/subagent/adapter.py` - SubAgent 适配器
- [ ] 产物2: `src/adapters/subagent/orchestrator.py` - 编排器（迁移）
- [ ] 产物3: `src/adapters/subagent/config.py` - 配置加载器（改造）
- [ ] 产物4: `tests/test_subagent_adapter.py` - 单元测试
