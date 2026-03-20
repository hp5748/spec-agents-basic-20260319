# 任务卡

## 基本信息
- **任务ID**: T008
- **标题**: SharedState 实现
- **负责角色**: developer
- **优先级**: P0
- **状态**: pending
- **创建时间**: 2026-03-20
- **依赖**: 无

## 背景说明

### 问题描述
主 Agent 和 SubAgent 需要共享上下文，避免重复传递信息。

### 核心目标
实现轻量级的上下文共享机制，支持主子 Agent 协作。

## 任务描述

实现 SharedState，包括：

1. **状态存储**
   - 对话历史（messages）
   - 工具调用结果（tool_results）
   - 上下文变量（context_vars）

2. **并发控制**
   - 线程安全（使用 asyncio.Lock）
   - 读写分离
   - 事务支持

3. **生命周期管理**
   - 创建（session 开始）
   - 更新（每次交互）
   - 清理（session 结束）

4. **序列化**
   - 支持持久化到 Memory
   - 支持从 Memory 恢复

## 技术约束

- 使用 `asyncio` 异步锁
- 内存高效（大数据不存储在 SharedState）
- 支持增量更新

## 验收标准
- [ ] 主子 Agent 能正确共享上下文
- [ ] 并发访问安全
- [ ] 状态持久化/恢复正常
- [ ] 内存占用可控

## 输出产物
- [ ] 产物1: `src/memory/shared_state.py` - SharedState 实现
- [ ] 产物2: `tests/test_shared_state.py` - 单元测试
