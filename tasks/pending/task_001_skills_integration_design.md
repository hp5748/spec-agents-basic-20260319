# 任务卡

## 基本信息
- **任务ID**: T001
- **标题**: Skills 集成架构设计
- **负责角色**: architect
- **优先级**: P0
- **状态**: pending
- **创建时间**: 2026-03-19
- **依赖**: 无

## 背景说明

### 问题描述
当前项目的 Skills（如 sqlite-query-skill）虽然定义完整，但没有集成到聊天流程中。用户输入"查询张三"时，系统直接调用 LLM 回答，而不是识别意图并调用对应的 Skill。

### 现有代码分析

**已存在的模块：**
- `skill_loader.py` - 可加载 Skill 元数据（keywords, intents, examples）
- `adapter_manager.py` - 适配器管理器
- `sqlite-query-skill/scripts/executor.py` - Skill 执行器

**缺失的功能：**
- 意图识别 - 识别用户输入匹配哪个 Skill
- Skill 路由 - 根据意图分发到对应 Skill
- 结果融合 - 将 Skill 执行结果融入响应

### sqlite-query-skill 示例

```yaml
# SKILL.md 元数据
name: sqlite-query-skill
intents:
  - database_query
  - person_search
keywords:
  - 查询
  - 人员
  - 搜索
examples:
  - "查询张三的信息"
  - "搜索姓李的员工"
```

## 任务描述

设计 Skills 集成架构，包括：

1. **意图识别模块** - 如何从用户输入识别意图
2. **Skill 路由器** - 如何将意图映射到 Skill
3. **执行流程** - 如何在 chat 流程中集成 Skill 调用
4. **结果处理** - 如何将 Skill 结果融入 LLM 响应

## 输出产物
- [ ] 架构设计文档: `spec/AI2AI/Skills集成架构设计.md`
- [ ] 包含：模块划分、接口定义、数据流图、伪代码

## 验收标准
- [ ] 架构设计清晰、可落地
- [ ] 兼容现有的 skill_loader.py 和 adapter_manager.py
- [ ] 支持多种 Skill 类型（Python、HTTP、MCP、Shell）
