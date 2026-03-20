# 任务卡

## 基本信息
- **任务ID**: T003
- **标题**: Python Adapter 实现
- **负责角色**: developer
- **优先级**: P0
- **状态**: pending
- **创建时间**: 2026-03-20
- **依赖**: T002

## 背景说明

### 问题描述
需要实现本地 Python Skills 的执行器，替换当前的 SkillExecutor。

### 核心目标
提供安全、可靠的本地代码执行能力。

## 任务描述

实现 Python Adapter，包括：

1. **执行器核心**
   - 继承 `BaseAdapter`
   - 实现 `execute()` 方法
   - 支持同步/异步函数调用

2. **安全沙箱**
   - 限制可访问的模块
   - 执行超时控制
   - 资源限制（内存/CPU）

3. **Skills 加载**
   - 扫描 `skills/` 目录
   - 加载 Skill 元数据
   - 注册到 ToolRegistry

4. **参数处理**
   - JSON → Python 对象转换
   - 参数验证
   - 错误提示

## 技术约束

- 使用 `asyncio` 异步执行
- 沙箱执行（考虑使用 RestrictedPython 或类似方案）
- 超时控制

## 验收标准
- [ ] 能正确执行本地 Skills
- [ ] 沙箱安全机制有效
- [ ] 超时控制生效
- [ ] 错误处理友好

## 输出产物
- [ ] 产物1: `src/adapters/python/executor.py` - Python 执行器
- [ ] 产物2: `src/adapters/python/sandbox.py` - 沙箱实现
- [ ] 产物3: `src/adapters/python/loader.py` - Skills 加载器
- [ ] 产物4: `tests/test_python_adapter.py` - 单元测试
