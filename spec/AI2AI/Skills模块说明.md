# Skills 模块说明

## 概述

Skills 是一个高级能力抽象层，用于扩展 Agent 的功能。

### 当前状态

| 功能 | 状态 | 说明 |
|------|------|------|
| Skill 元数据加载 | ✅ 已实现 | `src/skill_loader.py` |
| SKILL.md 解析 | ✅ 已实现 | YAML Front Matter |
| executor.py 动态加载 | ✅ 已实现 | `src/skill_executor.py` |
| 意图识别 | ✅ 已实现 | `src/intent/recognizer.py` |
| Skill 路由 | ✅ 已实现 | 已集成到 `StreamAgent` |
| Web API 集成 | ✅ 已实现 | `src/web/routes/chat.py` 使用 StreamAgent |
| 端到端验证 | ✅ 已验证 | 输入"查询张三"触发 sqlite-query-skill |

---

## 目录结构

```
skills/                           # 技能根目录
├── _skill-template/              # Skill 模板（复制创建新 Skill）
│   ├── SKILL.md                  # 核心指令 + 元数据（必需）
│   ├── templates/                # 常用模板
│   ├── examples/                 # 优秀/反例
│   ├── references/               # 规范、规则
│   └── scripts/
│       └── executor.py           # 执行脚本
│
├── sqlite-query-skill/           # SQLite 查询技能（已实现）
│   ├── SKILL.md
│   └── scripts/
│       └── executor.py
│
├── http-example-skill/           # HTTP 示例技能
│   └── SKILL.md
│
├── mcp-example-skill/            # MCP 示例技能
│   └── SKILL.md
│
└── shell-example-skill/          # Shell 示例技能
    └── SKILL.md
```

---

## SKILL.md 配置规范

### YAML Front Matter

```yaml
---
# ==========================================
# 基础元数据（必需）
# ==========================================
name: skill-name
description: 技能描述
version: 1.0.0
author: your-name
tags: [tag1, tag2]

# ==========================================
# 意图与触发（关键！）
# ==========================================
intents:
  - intent_code1
  - intent_code2
keywords:
  - 关键词1
  - 关键词2
examples:
  - "示例输入1"
  - "示例输入2"

# ==========================================
# 适配器配置
# ==========================================
adapter:
  type: python          # python / http / mcp / shell
  entry: scripts/executor.py

# ==========================================
# 执行配置
# ==========================================
execution:
  timeout: 30
  stream_enabled: true
---
```

---

## 核心数据类

### SkillResources（已实现）

```python
@dataclass
class SkillResources:
    skill_name: str
    skill_path: str
    instruction: str = ""           # SKILL.md 正文
    metadata: Dict[str, Any]        # YAML 元数据
    templates: List[TemplateContent]
    examples: List[ExampleContent]
    references: List[ReferenceContent]
    scripts: List[ScriptContent]
    loaded: bool = False
    errors: List[str]
```

### IntentResult（已实现）

```python
@dataclass
class IntentResult:
    skill_name: Optional[str]       # 匹配的 Skill 名称
    confidence: float               # 置信度 0.0-1.0
    matched_keywords: List[str]     # 匹配的关键词
    matched_intents: List[str]      # 匹配的意图
```

### SkillContext（已实现）

```python
@dataclass
class SkillContext:
    session_id: str
    user_input: str
    intent: str = ""
    chat_history: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### SkillResult（已实现）

```python
@dataclass
class SkillResult:
    success: bool
    response: str
    data: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
```

---

## 已实现技能

### sqlite-query-skill

**功能**：SQLite 数据库人员信息查询

```yaml
name: sqlite-query-skill
intents:
  - database_query
  - person_search
keywords:
  - 查询
  - 人员
  - 搜索
```

**使用方式**（CLI 测试）：
```python
from skills.sqlite-query-skill.scripts.executor import execute
result = execute({'user_input': '查询张三'}, {})
print(result['response'])
```

---

## 模块使用方式

### IntentRecognizer

```python
from src.intent import IntentRecognizer

recognizer = IntentRecognizer('skills')

# 识别意图
result = recognizer.recognize('查询张三')
print(result.skill_name)      # 'sqlite-query-skill'
print(result.confidence)      # 1.0
print(result.matched_keywords) # ['查询']
```

### SkillExecutor

```python
import asyncio
from src.skill_executor import SkillExecutor, SkillContext

async def test():
    executor = SkillExecutor('skills')

    context = SkillContext(
        session_id='test',
        user_input='查询张三',
        intent='database_query'
    )

    result = await executor.execute('sqlite-query-skill', context)
    print(result.success)   # True
    print(result.response)  # 查询结果

asyncio.run(test())
```

### StreamAgent（集成 Skill）

```python
import asyncio
from src.agent.stream_agent import StreamAgent

async def test():
    agent = StreamAgent('test-session')

    # Skill 匹配成功 → 直接返回 Skill 结果
    # Skill 未匹配 → 降级到 LLM
    async for chunk in agent.chat_stream('查询张三'):
        print(chunk, end='')

asyncio.run(test())
```

---

## 处理流程

```
用户输入
    ↓
StreamAgent.chat_stream()
    ↓
┌─────────────────────┐
│ 1. 初始化 Skill 系统 │
│ 2. 意图识别         │
│    ↓                │
│    有匹配 → 执行 Skill → 返回结果
│    无匹配 → 调用 LLM → 返回结果
└─────────────────────┘
    ↓
响应
```

---

## SkillLoader API

```python
from src.skill_loader import SkillLoader

loader = SkillLoader("skills")

# 列出所有 Skill
skills = loader.list_skills()

# 加载 Skill 元数据
metadata = loader.load_skill("sqlite-query-skill")

# 加载完整资源
resources = loader.load("skills/sqlite-query-skill")
```

---

*文档更新时间: 2026-03-19*
