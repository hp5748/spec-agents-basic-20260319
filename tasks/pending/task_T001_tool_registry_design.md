# 任务卡

## 基本信息
- **任务ID**: T001
- **标题**: ToolRegistry 设计与实现
- **负责角色**: architect
- **优先级**: P0
- **状态**: pending
- **创建时间**: 2026-03-20
- **依赖**: 无

## 背景说明

### 问题描述
当前架构中 Skills/MCP/SubAgent 分散管理，缺乏统一的工具注册表。需要实现一个中心化的 ToolRegistry 来管理所有类型的工具。

### 核心目标
实现"万物皆工具"理念，统一管理 Skills、MCP、SubAgent 等所有能力。

## 任务描述

设计并实现 ToolRegistry，包括：

1. **工具定义**
   - 定义统一的 Tool 数据结构（name, description, input_schema, handler）
   - 支持多种工具类型（Python/HTTP/MCP/SubAgent）

2. **注册表核心功能**
   - `register_tool()` - 注册工具
   - `get_tool()` - 获取工具
   - `list_tools()` - 列出所有工具
   - `to_openapi_schema()` - 导出 OpenAPI Function Calling 格式

3. **配置加载**
   - 自动加载 Skills 配置
   - 自动加载 MCP 配置
   - 自动加载 SubAgent 配置

4. **生命周期管理**
   - 工具初始化
   - 工具健康检查
   - 工具卸载

## 技术约束

- 必须兼容 DeepSeek-V3.2 的 Function Calling 格式
- 支持异步操作（asyncio）
- 线程安全

## 验收标准
- [ ] ToolRegistry 能正确注册所有类型工具
- [ ] `to_openapi_schema()` 能生成符合 OpenAPI 规范的 JSON Schema
- [ ] 支持动态添加/移除工具
- [ ] 单元测试覆盖率 > 80%

## 输出产物
- [ ] 产物1: `src/agent/tool_registry.py` - 工具注册表实现
- [ ] 产物2: `src/agent/tool.py` - 工具定义
- [ ] 产物3: `tests/test_tool_registry.py` - 单元测试
