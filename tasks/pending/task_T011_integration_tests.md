# 任务卡

## 基本信息
- **任务ID**: T011
- **标题**: 集成测试
- **负责角色**: tester
- **优先级**: P0
- **状态**: pending
- **创建时间**: 2026-03-20
- **依赖**: T007, T010

## 背景说明

### 问题描述
需要端到端测试整个 Agentic 流程，确保模块集成正确。

### 核心目标
验证完整的数据流：用户输入 → LLM 决策 → 工具执行 → 响应输出。

## 任务描述

编写集成测试，包括：

1. **完整流程测试**
   - 用户输入 → StreamAgent → ToolRegistry → Adapter → 响应
   - 测试所有工具类型（Skills/MCP/SubAgent/HTTP）

2. **场景测试**
   - 单工具调用
   - 多工具串行调用
   - 工具调用失败降级
   - 并发请求

3. **配置兼容测试**
   - `.claude/` 配置加载
   - `register/` 配置加载
   - 配置迁移

4. **性能测试**
   - 响应时间
   - 并发能力
   - 内存占用

## 技术约束

- 使用 `pytest` + `pytest-asyncio`
- 测试环境独立（使用 Docker 或虚拟环境）
- Mock 外部服务（LLM API）

## 验收标准
- [ ] 所有集成测试通过
- - [ ] 核心场景 100% 覆盖
- [ ] 性能指标达标
- [ ] 无内存泄漏

## 输出产物
- [ ] 产物1: `tests/integration/` 目录下的测试文件
- [ ] 产物2: `tests/integration/conftest.py` - 集成测试 fixtures
- [ ] 产物3: `tests/integration/docker-compose.yml` - 测试环境
- [ ] 产物4: 测试报告文档
