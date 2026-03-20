# 任务卡

## 基本信息
- **任务ID**: T002
- **标题**: Adapter 基类与工厂设计
- **负责角色**: architect
- **优先级**: P0
- **状态**: pending
- **创建时间**: 2026-03-20
- **依赖**: T001

## 背景说明

### 问题描述
当前适配器逻辑分散在各模块中，耦合度较高。需要设计统一的适配器基类和工厂，实现执行层彻底解耦。

### 核心目标
建立统一的适配器架构，让所有工具执行器遵循相同接口。

## 任务描述

设计 Adapter 基类与工厂，包括：

1. **类型定义**
   - `AdapterConfig` - 适配器配置
   - `ToolRequest` - 工具调用请求
   - `ToolResponse` - 工具调用响应
   - `AdapterType` - 适配器类型枚举

2. **适配器基类**
   - `BaseAdapter` - 定义统一接口
   - `async execute()` - 执行工具调用
   - `async health_check()` - 健康检查
   - `get_schema()` - 获取工具 Schema

3. **适配器工厂**
   - `AdapterFactory` - 根据 tool_config 创建对应 Adapter
   - `register_adapter_type()` - 注册新适配器类型
   - 支持动态扩展

4. **错误处理**
   - 统一的异常体系
   - 错误恢复机制
   - 降级策略

## 技术约束

- 使用抽象基类（ABC）
- 支持异步操作
- 类型提示完整

## 验收标准
- [ ] 所有适配器遵循统一接口
- [ ] AdapterFactory 能正确路由到对应适配器
- [ ] 支持动态注册新适配器类型
- [ ] 异常处理完善

## 输出产物
- [ ] 产物1: `src/adapters/core/types.py` - 类型定义
- [ ] 产物2: `src/adapters/core/base.py` - 适配器基类
- [ ] 产物3: `src/adapters/core/factory.py` - 适配器工厂
- [ ] 产物4: `tests/test_adapter_factory.py` - 单元测试
