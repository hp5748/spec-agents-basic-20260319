---
# ==========================================
# 基础元数据（必需）
# ==========================================
name: skill-template
description: Skill 模板 - 创建新 Skill 时复制此目录
version: 2.0.0
author: your-name
tags: [template, example]

# ==========================================
# 分类与优先级
# ==========================================
tier: CORE              # CORE / POWERFUL / SPECIALIZED
category: general       # engineering / business / data / ...
priority: 10

# ==========================================
# 意图与触发
# ==========================================
intents:
  - example_intent
keywords:
  - 关键词1
  - 关键词2
examples:
  - "示例输入1"
  - "示例输入2"

# ==========================================
# 适配器配置（核心）
# ==========================================
# 支持的适配器类型：
# - python: 执行 Skill 内置脚本（默认）
# - http:   调用 REST API（需配置 OpenAPI）
# - mcp:    连接 MCP Server
# - shell:  执行命令行工具（沙箱安全）
adapter:
  type: python
  entry: scripts/executor.py

  # 备用适配器（可选）
  alternatives:
    # HTTP 适配器配置
    - type: http
      adapter_name: order-api       # 引用 config/adapters.yaml 中的配置
      # 或内联配置
      base_url: https://api.example.com
      openapi_path: adapters/http/specs/example-api.yaml
      auth:
        type: bearer
        token_env: API_TOKEN
      endpoint: /orders/{orderId}
      method: GET

    # MCP 适配器配置
    - type: mcp
      adapter_name: echo-server
      # 或内联配置
      server_path: adapters/mcp/servers/echo/server.py
      transport: stdio              # stdio / sse / streamable-http
      tool_name: echo

    # Shell 适配器配置
    - type: shell
      adapter_name: git-tools
      # 或内联配置
      work_dir: ${PROJECT_ROOT}
      sandbox: true
      allowed_commands:
        - git
        - npm

# ==========================================
# 输入输出 Schema（JSON Schema 格式）
# ==========================================
input_schema:
  type: object
  properties:
    query:
      type: string
      description: 查询内容
    options:
      type: object
      properties:
        detailed:
          type: boolean
          default: false
  required: [query]

output_schema:
  type: object
  properties:
    result:
      type: string
      description: 处理结果
    success:
      type: boolean
    data:
      type: object
      description: 结构化数据

# ==========================================
# 执行配置
# ==========================================
execution:
  timeout: 30
  stream_enabled: true
  load_templates: true
  load_examples: true
  load_references: true

# ==========================================
# 重试配置（可选）
# ==========================================
retry:
  max_attempts: 3
  strategy: exponential           # exponential / linear / fixed
  base_delay: 1.0
  max_delay: 30.0
  retryable_errors:
    - timeout
    - rate_limit
    - connection_error

# ==========================================
# 降级配置（可选）
# ==========================================
fallback:
  strategy: llm_assist            # llm_assist / cached / custom
  message: "服务暂时不可用，请稍后重试"
  cache_ttl: 300                  # 缓存时间（秒）

# ==========================================
# 依赖声明（可选）
# ==========================================
dependencies:
  skills:
    - logistics-assistant>=1.0.0
  adapters:
    - http                        # 需要 HTTP 适配器
  python:
    - requests>=2.28.0
    - pydantic>=2.0.0

# ==========================================
# 权限与安全（可选）
# ==========================================
permissions:
  network:
    - host: api.example.com
      port: 443
  filesystem:
    - path: /tmp/skills/
      mode: rw                    # r / w / rw
  env_vars:
    - API_KEY
    - DATABASE_URL
---

# Skill 模板

## 功能说明

这里是 Skill 的详细功能说明。

## 使用方法

### 基本用法
```
用户：示例输入
助手：示例响应
```

### 高级用法
```
用户：高级示例
助手：高级响应
```

## 目录结构

```
skill-template/
├── SKILL.md              # 本文件（核心指令 + 元数据）
├── templates/            # 常用模板（Claude 按需读取）
│   └── example-template.md
├── examples/             # 优秀/反例（给 Claude 看标准）
│   ├── good-example.md
│   └── anti-pattern.md
├── references/           # 规范、规则、禁用词表
│   └── conventions.md
└── scripts/              # 可执行脚本
    └── executor.py
```

## 适配器类型

### Python 适配器（默认）

执行 Skill 内置的 Python 脚本：

```yaml
adapter:
  type: python
  entry: scripts/executor.py
```

### HTTP 适配器

调用 REST API：

```yaml
adapter:
  type: http
  base_url: https://api.example.com
  openapi_path: adapters/http/specs/api.yaml
  auth:
    type: bearer
    token_env: API_TOKEN
```

### MCP 适配器

连接 MCP Server：

```yaml
adapter:
  type: mcp
  server_path: adapters/mcp/servers/echo/server.py
  transport: stdio
```

### Shell 适配器

执行命令行工具：

```yaml
adapter:
  type: shell
  work_dir: ${PROJECT_ROOT}
  sandbox: true
  allowed_commands:
    - git
    - npm
```

## 实现说明

执行器位于 `scripts/executor.py`，实现 `SkillExecutor` 类：

```python
from dataclasses import dataclass, field
from typing import Any, Dict

@dataclass
class SkillResult:
    success: bool
    response: str
    data: Dict[str, Any] = field(default_factory=dict)
    error: str = ""

@dataclass
class SkillContext:
    session_id: str
    user_input: str
    intent: str
    chat_history: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

class SkillExecutor:
    async def execute(self, context: SkillContext) -> SkillResult:
        # 实现逻辑
        pass
```

## 注意事项

- 注意事项1
- 注意事项2
