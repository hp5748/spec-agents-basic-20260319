# 任务索引

## Agentic 架构重构任务列表

**项目**: Super Agent v2.0.0 - Agentic 架构全量重构
**创建时间**: 2026-03-20
**PRD**: `spec/Me2AI/prd_agentic_refactor_20260320.md`

---

## 任务统计

- **总任务数**: 12
- **待开始**: 12
- **进行中**: 0
- **已完成**: 0

---

## 任务列表

### Phase 1: 基础设施 (架构师)

| 任务ID | 标题 | 负责角色 | 优先级 | 预计工时 | 文件 |
|--------|------|----------|--------|----------|------|
| T001 | ToolRegistry 设计与实现 | architect | P0 | 4h | [task_T001_tool_registry_design.md](./task_T001_tool_registry_design.md) |
| T002 | Adapter 基类与工厂设计 | architect | P0 | 3h | [task_T002_adapter_factory_design.md](./task_T002_adapter_factory_design.md) |

### Phase 2: 适配器实现 (开发者 - 可并行)

| 任务ID | 标题 | 负责角色 | 优先级 | 预计工时 | 依赖 | 文件 |
|--------|------|----------|--------|----------|------|------|
| T003 | Python Adapter 实现 | developer | P0 | 6h | T002 | [task_T003_python_adapter_impl.md](./task_T003_python_adapter_impl.md) |
| T004 | HTTP Adapter 实现 | developer | P0 | 4h | T002 | [task_T004_http_adapter_impl.md](./task_T004_http_adapter_impl.md) |
| T005 | MCP Adapter 迁移 | developer | P0 | 5h | T002 | [task_T005_mcp_adapter_migration.md](./task_T005_mcp_adapter_migration.md) |
| T006 | SubAgent Adapter 迁移 | developer | P0 | 5h | T002 | [task_T006_subagent_adapter_migration.md](./task_T006_subagent_adapter_migration.md) |
| T008 | SharedState 实现 | developer | P0 | 4h | 无 | [task_T008_shared_state_impl.md](./task_T008_shared_state_impl.md) |
| T009 | 配置兼容层实现 | developer | P0 | 3h | T001 | [task_T009_config_compat_layer.md](./task_T009_config_compat_layer.md) |

### Phase 3: 核心重构 (开发者)

| 任务ID | 标题 | 负责角色 | 优先级 | 预计工时 | 依赖 | 文件 |
|--------|------|----------|--------|----------|------|------|
| T007 | StreamAgent 重构 | developer | P0 | 8h | T001, T002, T008 | [task_T007_stream_agent_refactor.md](./task_T007_stream_agent_refactor.md) |

### Phase 4: 测试验证 (测试工程师)

| 任务ID | 标题 | 负责角色 | 优先级 | 预计工时 | 依赖 | 文件 |
|--------|------|----------|--------|----------|------|------|
| T010 | 单元测试 | tester | P0 | 8h | T001-T009 | [task_T010_unit_tests.md](./task_T010_unit_tests.md) |
| T011 | 集成测试 | tester | P0 | 6h | T007, T010 | [task_T011_integration_tests.md](./task_T011_integration_tests.md) |

### Phase 5: 代码审查与交付 (审查者)

| 任务ID | 标题 | 负责角色 | 优先级 | 预计工时 | 依赖 | 文件 |
|--------|------|----------|--------|----------|------|------|
| T012 | 代码审查与文档更新 | reviewer | P1 | 4h | T011 | [task_T012_code_review.md](./task_T012_code_review.md) |

---

## 推荐执行顺序

### 第 1 周 (14h)
1. **T001** (4h) - ToolRegistry 设计与实现
2. **T002** (3h) - Adapter 基类与工厂设计
3. **T008** (4h) - SharedState 实现（可并行）
4. **T009** (3h) - 配置兼容层实现（可并行）

### 第 2 周 (20h - 可并行)
1. **T003** (6h) - Python Adapter 实现
2. **T004** (4h) - HTTP Adapter 实现
3. **T005** (5h) - MCP Adapter 迁移
4. **T006** (5h) - SubAgent Adapter 迁移

### 第 3 周 (8h)
1. **T007** (8h) - StreamAgent 重构

### 第 4 周 (14h)
1. **T010** (8h) - 单元测试
2. **T011** (6h) - 集成测试

### 第 5 周 (4h)
1. **T012** (4h) - 代码审查与文档更新

**总计**: 约 60 工时（单人 8 周或 4 人团队 2 周）

---

## 关键路径

```
T001 (ToolRegistry)
  ↓
T002 (Adapter Factory)
  ↓
T003/T004/T005/T006 (Adapters 并行)
  ↓
T007 (StreamAgent 重构)
  ↓
T010 (单元测试)
  ↓
T011 (集成测试)
  ↓
T012 (代码审查)
```

---

## 注意事项

1. **必须完成的任务**: T001-T011 (P0)
2. **可并行任务**: T003-T006, T008-T009
3. **关键依赖**:
   - T007 依赖 T001, T002, T008
   - T011 依赖 T007, T010
   - 所有 Adapter 实现依赖 T002
4. **配置迁移**: 建议在 T009 完成后进行配置迁移

---

*最后更新: 2026-03-20*
