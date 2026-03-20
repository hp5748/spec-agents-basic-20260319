# 产品需求文档 (PRD)
## MCP 与 SubAgent 模块开发

## 元信息
- **项目名称**: Super Agent - MCP & SubAgent 模块
- **版本**: 1.0.0
- **创建时间**: 2026-03-19
- **创建者**: PM Agent

---

## 1. 项目概述

### 1.1 背景
当前项目已实现 Skills 模块（意图识别 + Skill 执行），需要扩展 MCP (Model Context Protocol) 和 SubAgent 能力，使系统具备：
- 连接外部 MCP 服务的能力（如 GitHub、数据库、文件系统）
- 多 Agent 协作能力（任务分解、专业分工）

### 1.2 目标
- 实现 MCP 模块，兼容 Claude Code 的 JSON 配置方式
- 实现 SubAgent 模块，支持多 Agent 编排
- 将两者集成到 StreamAgent 中

---

## 2. 功能需求

### 2.1 MCP 模块 (P0)

| 功能ID | 功能名称 | 优先级 | 描述 |
|--------|----------|--------|------|
| MCP-001 | 配置加载器 | P0 | 支持 .claude/mcp.json 和 ~/.claude.json |
| MCP-002 | STDIO 传输 | P0 | 连接本地 MCP Server 进程 |
| MCP-003 | HTTP 传输 | P0 | 连接远程 MCP Server |
| MCP-004 | 工具调用 | P0 | call_tool、list_tools |
| MCP-005 | 环境变量展开 | P0 | 支持 $VAR 语法 |

### 2.2 SubAgent 模块 (P0)

| 功能ID | 功能名称 | 优先级 | 描述 |
|--------|----------|--------|------|
| SUB-001 | 目录扫描器 | P0 | 自动扫描 subagents/ 目录（项目根目录下，与 skills/ 平级） |
| SUB-002 | Agent 基类 | P0 | SubAgent 基类和接口定义 |
| SUB-003 | 编排器 | P0 | 路由、并行执行、链式调用 |
| SUB-004 | 触发机制 | P0 | can_handle() 方法，支持关键词/LLM 判断 |

### 2.3 集成功能 (P0)

| 功能ID | 功能名称 | 优先级 | 描述 |
|--------|----------|--------|------|
| INT-001 | StreamAgent 集成 | P0 | 统一路由 Skills/MCP/SubAgent |
| INT-002 | 统一能力注册表 | P0 | 跨类型能力查找 |
| INT-003 | 配置示例 | P1 | 示例配置文件 |

---

## 3. 非功能性需求

- **兼容性**: 配置格式与 Claude Code 完全兼容
- **性能**: MCP 连接异步初始化，不阻塞启动
- **可扩展性**: 支持自定义传输方式
- **安全性**: 敏感信息通过环境变量传递

---

## 4. 技术约束

- 配置格式: JSON（Claude Code 标准）
- 传输协议: STDIO、HTTP、SSE
- 异步框架: asyncio
- 数据类: dataclasses

---

## 5. 验收标准

- [ ] MCP 配置加载器能正确解析 .claude/mcp.json
- [ ] MCP 客户端能连接并调用外部 MCP Server
- [ ] SubAgent 扫描器能自动发现 subagents/ 目录下的 Agent
- [ ] SubAgentOrchestrator 能正确路由任务
- [ ] StreamAgent 能统一调用 Skills/MCP/SubAgent
- [ ] AI2AI 文档已更新

---

## 6. 文件清单

### 新增文件
- `src/mcp/__init__.py`
- `src/mcp/config.py`
- `src/mcp/client.py`
- `src/mcp/transport/stdio.py`
- `src/mcp/transport/http.py`
- `src/mcp/transport/__init__.py`
- `src/subagent/__init__.py`
- `src/subagent/config.py`
- `src/subagent/base_agent.py`
- `src/subagent/orchestrator.py`
- `.claude/mcp.json`
- `.claude/README.md`
- `spec/AI2AI/MCP模块说明.md`
- `spec/AI2AI/SubAgent模块说明.md`
- `subagents/_subagent-template/` (Agent 模板目录)
  - `agent.py`
  - `AGENT.md`
  - `prompts/system.md`
- `subagents/code-analyzer/` (示例: 代码分析 Agent)
  - `agent.py`
  - `AGENT.md`
  - `prompts/system.md`
- `subagents/web-scraper/` (示例: 网页抓取 Agent)
  - `agent.py`
  - `AGENT.md`
  - `prompts/system.md`

### 修改文件
- `src/agent/stream_agent.py` - 集成 MCP 和 SubAgent
- `spec/AI2AI/架构设计.md` - 更新架构图

---

*PRD 创建时间: 2026-03-19*
