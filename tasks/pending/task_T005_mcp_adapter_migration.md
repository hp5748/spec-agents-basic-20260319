# 任务卡

## 基本信息
- **任务ID**: T005
- **标题**: MCP Adapter 迁移
- **负责角色**: developer
- **优先级**: P0
- **状态**: pending
- **创建时间**: 2026-03-20
- **依赖**: T002

## 背景说明

### 问题描述
将现有的 `src/mcp/` 模块迁移到 `src/adapters/mcp/`，并改造为符合新架构的 Adapter。

### 核心目标
保持 MCP 功能不变，同时适配新的 Adapter 接口。

## 任务描述

迁移并改造 MCP 模块，包括：

1. **目录迁移**
   - 移动 `src/mcp/` → `src/adapters/mcp/`
   - 更新所有 import 路径

2. **适配器改造**
   - 创建 `MCPAdapter` 继承 `BaseAdapter`
   - 实现新的 `execute()` 接口
   - 保持原有 MCP 协议逻辑

3. **配置兼容**
   - 支持 `.claude/mcp.json` 格式
   - 支持 `register/mcp.json` 格式
   - 自动检测并加载

4. **工具注册**
   - 将 MCP Server 的 tools 注册到 ToolRegistry
   - 动态更新工具列表

## 技术约束

- 保持向后兼容
- 支持标准 MCP 协议
- 异步操作

## 验收标准
- [ ] 迁移后所有原有功能正常
- [ ] 符合 Adapter 接口规范
- [ ] 配置加载兼容两种格式
- [ ] 工具自动注册生效

## 输出产物
- [ ] 产物1: `src/adapters/mcp/adapter.py` - MCP 适配器
- [ ] 产物2: `src/adapters/mcp/client.py` - MCP 客户端（迁移）
- [ ] 产物3: `src/adapters/mcp/config.py` - 配置加载器（改造）
- [ ] 产物4: `tests/test_mcp_adapter.py` - 单元测试
