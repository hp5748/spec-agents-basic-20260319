---
# ==========================================
# 基础元数据
# ==========================================
name: http-example-skill
description: HTTP 适配器示例 Skill - 展示如何通过 HTTP 适配器调用 REST API
version: 1.0.0
author: super-agent-team
tags: [http, api, example, demo]

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
  - api_demo
  - http_example
keywords:
  - HTTP
  - API
  - 示例
  - demo
examples:
  - "演示 HTTP 适配器"
  - "调用示例 API"

# ==========================================
# 适配器配置（HTTP）
# ==========================================
adapter:
  type: http
  base_url: https://jsonplaceholder.typicode.com
  # 使用内联 OpenAPI 规范（简化示例）
  # 实际项目中建议使用 openapi_path
  endpoints:
    - name: list_posts
      method: GET
      path: /posts
      description: 获取文章列表
    - name: get_post
      method: GET
      path: /posts/{id}
      description: 获取单篇文章
    - name: create_post
      method: POST
      path: /posts
      description: 创建文章

# ==========================================
# 输入输出 Schema
# ==========================================
input_schema:
  type: object
  properties:
    action:
      type: string
      enum: [list, get, create]
      description: 操作类型
    post_id:
      type: integer
      description: 文章ID（get 操作需要）
    title:
      type: string
      description: 文章标题（create 操作需要）
    body:
      type: string
      description: 文章内容（create 操作需要）
    userId:
      type: integer
      description: 用户ID（create 操作需要）
  required: [action]

output_schema:
  type: object
  properties:
    success:
      type: boolean
    data:
      type: object
      description: API 返回的数据
    message:
      type: string

# ==========================================
# 执行配置
# ==========================================
execution:
  timeout: 30
  stream_enabled: false

# ==========================================
# 依赖声明
# ==========================================
dependencies:
  adapters:
    - http
---

# HTTP 适配器示例 Skill

## 功能说明

这是一个示例 Skill，展示如何使用 HTTP 适配器调用 REST API。

本 Skill 使用 [JSONPlaceholder](https://jsonplaceholder.typicode.com/) 作为演示 API。

## 使用方法

### 列出文章
```
用户：列出所有文章
助手：正在获取文章列表...
```

### 获取单篇文章
```
用户：获取文章 1
助手：正在获取文章 1 的详情...
```

### 创建文章
```
用户：创建一篇文章，标题是"测试文章"
助手：正在创建文章...
```

## 适配器配置说明

### 基本配置

```yaml
adapter:
  type: http
  base_url: https://api.example.com
```

### 使用 OpenAPI 规范

```yaml
adapter:
  type: http
  base_url: https://api.example.com
  openapi_path: adapters/http/specs/api.yaml
  auth:
    type: bearer
    token_env: API_TOKEN
```

### 调用方式

在 `scripts/executor.py` 中：

```python
# 方式 1：通过 operation_id
result = await adapter.execute(
    context,
    {
        "operation_id": "get_post",
        "id": 1
    }
)

# 方式 2：直接指定端点
result = await adapter.execute(
    context,
    {
        "endpoint": "/posts/1",
        "method": "GET"
    }
)
```

## 注意事项

- 生产环境请配置认证（auth）
- 建议使用 OpenAPI 规范文件
- 设置合理的超时时间
- 处理 API 错误响应
