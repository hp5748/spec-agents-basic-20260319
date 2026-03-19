---
# ==========================================
# 基础元数据
# ==========================================
name: shell-example-skill
description: Shell 适配器示例 Skill - 展示如何安全执行命令行工具
version: 1.0.0
author: super-agent-team
tags: [shell, git, example, demo]

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
  - shell_demo
  - git_status
keywords:
  - git
  - shell
  - 命令
  - status
examples:
  - "查看 git 状态"
  - "执行 git log"

# ==========================================
# 适配器配置（Shell）
# ==========================================
adapter:
  type: shell
  work_dir: ${PROJECT_ROOT}
  sandbox: true
  allowed_commands:
    - git
    - npm
    - pip
  max_output_size: 65536

# ==========================================
# 输入输出 Schema
# ==========================================
input_schema:
  type: object
  properties:
    command:
      type: string
      enum: [status, log, diff, branch]
      description: Git 命令类型
    args:
      type: array
      items:
        type: string
      description: 命令参数
  required: [command]

output_schema:
  type: object
  properties:
    success:
      type: boolean
    output:
      type: string
    command:
      type: string

# ==========================================
# 执行配置
# ==========================================
execution:
  timeout: 60

# ==========================================
# 依赖声明
# ==========================================
dependencies:
  adapters:
    - shell
---

# Shell 适配器示例 Skill

## 功能说明

这是一个示例 Skill，展示如何使用 Shell 适配器安全执行命令行工具。

本 Skill 使用 Git 命令作为演示。

## 使用方法

### 查看状态
```
用户：git status
助手：执行 git status...
On branch main
Your branch is up to date...
```

### 查看日志
```
用户：git log --oneline -5
助手：执行 git log...
abc1234 (HEAD) Latest commit
...
```

## 适配器配置说明

### 基本配置

```yaml
adapter:
  type: shell
  work_dir: /project
  sandbox: true
```

### 命令白名单

```yaml
adapter:
  type: shell
  sandbox: true
  allowed_commands:
    - git
    - npm
    - pip
    - python
```

### 资源限制

```yaml
adapter:
  type: shell
  timeout: 60
  max_output_size: 1048576  # 1MB
```

## 安全机制

### 白名单模式
只有 `allowed_commands` 中的命令可以执行。

### 黑名单模式
以下命令始终被禁止：
- 系统破坏：rm -rf /, mkfs, dd
- 权限提升：sudo, chmod 777
- 网络危险：nc -l, iptables
- Fork 炸弹：:(){ :|:& };:

### 危险模式检测
正则表达式检测危险命令模式。

## 调用方式

在 `scripts/executor.py` 中：

```python
from adapters.shell import ShellAdapter, create_executor

async def execute(context):
    executor = create_executor(
        work_dir="/project",
        allowed_commands={"git", "npm"}
    )

    # 验证命令
    is_valid, error = executor.validate("git status")
    if not is_valid:
        return SkillResult(success=False, error=error)

    # 执行命令
    result = await executor.execute("git status")

    return SkillResult(
        success=result.success,
        response=result.stdout
    )
```

## 允许的命令示例

| 命令 | 用途 |
|------|------|
| git | 版本控制 |
| npm/yarn/pnpm | 包管理 |
| pip/poetry | Python 包管理 |
| docker | 容器操作 |
| kubectl | Kubernetes |
| python/node | 语言运行时 |

## 注意事项

- 沙箱模式下禁止写入操作
- 注意命令超时设置
- 处理命令执行失败
- 捕获和处理输出
