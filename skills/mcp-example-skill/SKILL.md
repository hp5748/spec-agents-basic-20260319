---
# ==========================================
# 基础元数据
# ==========================================
name: mcp-example-skill
description: MCP 适配器示例 Skill - 展示如何通过 MCP 适配器连接 MCP Server
version: 1.0.0
author: super-agent-team
tags: [mcp, example, demo]

# ==========================================
# 分类与优先级
# ==========================================
tier: SPECIALIZED
category: example
priority: 5

# ==========================================
# 意图与触发
# ==========================================
intents:
  - mcp_demo
  - echo_test
keywords:
  - MCP
  - echo
  - 示例
examples:
  - "测试 MCP 连接"
  - "回显消息"

# ==========================================
# 适配器配置（MCP）
# ==========================================
adapter:
  type: mcp
  server_path: adapters/mcp/servers/echo/server.py
  transport: stdio
  tools:
    - name: echo
      description: 回显消息
    - name: reverse
      description: 反转字符串

# ==========================================
# 输入输出 Schema
# ==========================================
input_schema:
  type: object
  properties:
    tool:
      type: string
      enum: [echo, reverse]
      default: echo
    message:
      type: string
      description: 要处理的消息
  required: [message]

output_schema:
  type: object
  properties:
    success:
      type: boolean
    result:
      type: string
    tool:
      type: string

# ==========================================
# 执行配置
# ==========================================
execution:
  timeout: 30

# ==========================================
# 依赖声明
# ==========================================
dependencies:
  adapters:
    - mcp
---

# MCP 适配器示例 Skill

## 功能说明

这是一个示例 Skill，展示如何使用 MCP 适配器连接 MCP Server。

本 Skill 使用内置的 Echo MCP Server 作为演示。

## 使用方法

### 回显消息
```
用户：echo 你好世界
助手：Echo: 你好世界
```

### 反转字符串
```
用户：reverse Hello
助手：olleH
```

## 适配器配置说明

### stdio 传输（本地进程）

```yaml
adapter:
  type: mcp
  server_path: adapters/mcp/servers/echo/server.py
  transport: stdio
```

### SSE 传输（远程服务）

```yaml
adapter:
  type: mcp
  server_url: https://mcp-server.example.com/sse
  transport: sse
  headers:
    Authorization: Bearer ${MCP_TOKEN}
```

### streamable-http 传输

```yaml
adapter:
  type: mcp
  server_url: https://mcp-server.example.com
  transport: streamable-http
```

## 调用方式

在 `scripts/executor.py` 中：

```python
from adapters.mcp import MCPClient

async def execute(context):
    async with MCPClient(
        transport_type="stdio",
        transport_config={"server_path": "adapters/mcp/servers/echo/server.py"}
    ) as client:
        # 列出工具
        tools = await client.list_tools()

        # 调用工具
        result = await client.call_tool("echo", {"message": "Hello"})

        return SkillResult(
            success=True,
            response=result[0]["text"]
        )
```

## 可用工具

### echo
回显输入的消息。

**参数**：
- `message` (string): 要回显的消息

### reverse
反转输入的字符串。

**参数**：
- `text` (string): 要反转的文本

## 注意事项

- stdio 传输仅适用于本地进程
- 远程服务需要配置认证
- 处理超时和错误情况
