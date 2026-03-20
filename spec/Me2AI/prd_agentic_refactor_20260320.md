# 产品需求文档 (PRD)
## Agentic 架构全量重构

## 元信息
- **项目名称**: Super Agent - Agentic 架构重构
- **版本**: 2.0.0
- **创建时间**: 2026-03-20
- **创建者**: PM Agent
- **架构理念**: "万物皆工具 (Everything is a Tool)"

---

## 1. 项目概述

### 1.1 背景
当前架构存在以下问题：
- 硬编码的意图识别优先级（P0/P1/P2）缺乏灵活性
- Skills/MCP/SubAgent 分散管理，缺乏统一工具注册表
- 适配器逻辑分散在各模块中，耦合度较高

### 1.2 目标
实现真正的 Agentic 架构，让大模型自主决策：
- **LLM 驱动**: 废弃规则路由，全面拥抱 Function Calling
- **统一注册表**: Tool Registry 管理所有能力
- **适配器解耦**: 执行层彻底解耦

---

## 2. 核心设计原则

| 原则 | 说明 |
|------|------|
| **LLM-Driven** | 大模型自主决策调用哪个工具，而非硬编码规则 |
| **Everything is a Tool** | Skills/MCP/SubAgent 统一为 Tool 概念 |
| **适配器解耦** | 执行层独立演进，与决策层分离 |
| **配置兼容** | 同时支持 `.claude/` 和 `register/` 目录 |

---

## 3. 功能需求

### 3.1 核心大脑层重构 (P0)

| 功能ID | 功能名称 | 优先级 | 描述 |
|--------|----------|--------|------|
| CORE-001 | 废弃 IntentRecognizer | P0 | 移除 `src/intent/recognizer.py` |
| CORE-002 | 实现 ToolRegistry | P0 | 统一工具注册表 `src/agent/tool_registry.py` |
| CORE-003 | 重构 StreamAgent | P0 | 基于 Function Calling 重写 `src/agent/stream_agent.py` |
| CORE-004 | 实现 SharedState | P0 | 主子智能体上下文共享 `src/memory/shared_state.py` |

### 3.2 适配器层重构 (P0)

| 功能ID | 功能名称 | 优先级 | 描述 |
|--------|----------|--------|------|
| ADP-001 | 适配器基类与工厂 | P0 | `src/adapters/core/factory.py`, `types.py` |
| ADP-002 | Python 适配器 | P0 | 本地 Skills 执行器 `src/adapters/python/` |
| ADP-003 | HTTP 适配器 | P0 | REST API 客户端 `src/adapters/http/` |
| ADP-004 | MCP 适配器迁移 | P0 | `src/mcp/` → `src/adapters/mcp/` |
| ADP-005 | SubAgent 适配器 | P0 | `src/subagent/` → `src/adapters/subagent/` |

### 3.3 配置兼容层 (P0)

| 功能ID | 功能名称 | 优先级 | 描述 |
|--------|----------|--------|------|
| CFG-001 | 配置加载器 | P0 | 同时支持 `.claude/` 和 `register/` |
| CFG-002 | 向后兼容 | P0 | 自动检测并加载两种配置格式 |

### 3.4 目录结构调整 (P0)

| 操作 | 源路径 | 目标路径 |
|------|--------|----------|
| 移动 | `src/mcp/` | `src/adapters/mcp/` |
| 移动 | `src/subagent/` | `src/adapters/subagent/` |
| 新增 | - | `src/agent/tool_registry.py` |
| 新增 | - | `src/memory/shared_state.py` |
| 新增 | - | `register/` (配置目录) |

---

## 4. 数据流向设计

### 4.1 标准 Agentic Flow

```
1. 用户输入 → FastAPI 接收 → 生成 session_id

2. 感知阶段:
   ├─ StreamAgent 从 MemoryManager 提取对话摘要
   └─ 从 ToolRegistry 拉取可用工具清单

3. 规划阶段 (LLM 决策):
   ├─ Agent 发送请求到 DeepSeek-V3.2
   ├─ 附加 tools 参数 (所有可用工具的 JSON Schema)
   └─ LLM 返回 tool_calls 或直接文本响应

4. 执行阶段:
   ├─ 如需调用工具 → AdapterFactory 路由到对应 Adapter
   ├─ Python Adapter → 执行本地 Skills
   ├─ HTTP Adapter → 调用外部 REST API
   ├─ MCP Adapter → 调用 MCP Server
   └─ SubAgent Adapter → 唤起子智能体

5. 整合阶段:
   ├─ 收集 Adapter 执行结果
   ├─ 附加到上下文
   └─ 再次请求 LLM 进行自然语言总结

6. 输出阶段:
   ├─ 通过 SSE 流式推送到前端
   └─ 持久化到 Memory
```

---

## 5. 技术约束

| 约束项 | 说明 |
|--------|------|
| 大模型 | DeepSeek-V3.2，支持 Function Calling |
| 配置格式 | JSON (Claude Code 标准) |
| 异步框架 | asyncio |
| 目录兼容 | 同时支持 `.claude/` 和 `register/` |

---

## 6. 验收标准

### 6.1 功能验收
- [ ] ToolRegistry 能正确注册所有类型工具 (Skills/MCP/SubAgent)
- [ ] StreamAgent 能通过 Function Calling 调用任意工具
- [ ] 所有 Adapter 正常工作并返回标准格式结果
- [ ] 配置加载器同时支持 `.claude/` 和 `register/`

### 6.2 代码质量
- [ ] `src/intent/` 目录已移除
- [ ] `src/mcp/` 和 `src/subagent/` 已迁移到 `src/adapters/`
- [ ] 代码无硬编码优先级规则

### 6.3 文档验收
- [ ] AI2AI 架构文档已更新
- [ ] README.md 已更新
- [ ] 配置说明文档完整

---

## 7. 文件清单

### 新增文件
- `src/agent/tool_registry.py` - 工具注册表
- `src/agent/tool.py` - 工具定义
- `src/memory/shared_state.py` - 上下文共享
- `src/adapters/core/factory.py` - 适配器工厂
- `src/adapters/core/types.py` - 类型定义
- `src/adapters/python/executor.py` - Python 执行器
- `src/adapters/http/client.py` - HTTP 客户端
- `src/adapters/mcp/` (从 src/mcp/ 迁移)
- `src/adapters/subagent/` (从 src/subagent/ 迁移)
- `register/mcp.json` - MCP 配置
- `register/agents.json` - SubAgent 配置

### 删除文件
- `src/intent/recognizer.py`
- `src/intent/__init__.py`
- `src/skill_executor.py` (功能迁移到 adapters/python/)

### 修改文件
- `src/agent/stream_agent.py` - 重构为 Function Calling 模式
- `src/llm_client.py` - 支持 tools 参数
- `src/web/main.py` - 初始化 ToolRegistry
- `spec/AI2AI/架构设计.md` - 更新架构图
- `spec/AI2AI/Adapters模块说明.md` - 新增
- `README.md` - 更新使用说明

---

## 8. 实施计划

### Phase 1: 基础设施 (架构师)
- ToolRegistry 设计与实现
- Adapter 基类与工厂
- 配置兼容层

### Phase 2: 适配器迁移 (开发者)
- Python Adapter 实现
- HTTP Adapter 实现
- MCP/SubAgent 迁移

### Phase 3: 核心重构 (开发者)
- StreamAgent 重构
- LLM Client 扩展
- SharedState 实现

### Phase 4: 测试验证 (测试工程师)
- 单元测试
- 集成测试
- 端到端验证

### Phase 5: 代码审查 (审查者)
- 代码质量检查
- 文档完整性检查

---

## 9. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| LLM Function Calling 不稳定 | 高 | 保留降级方案配置项 |
| 目录迁移导致路径错误 | 中 | 更新所有 import 路径 |
| 配置兼容性测试不充分 | 中 | 充分测试两种配置格式 |

---

*PRD 创建时间: 2026-03-20*
