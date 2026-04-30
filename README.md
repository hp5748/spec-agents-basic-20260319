# Super Agent to Skill

将 Agent 能力转化为可复用 Skill 的工具集。

## 项目概述

这是一个将 Agent 能力转化为可复用 Skill 的工具集，核心特性：

- **AI 团队协作**：PM、架构师、开发者等多角色协作
- **通用适配器层**：支持 Python、HTTP、MCP、SubAgent 四种执行方式
- **Spec 驱动开发**：Me2AI（用户意图）+ AI2AI（代码状态）分层管理
- **Agentic 架构**：基于 Function Calling 的智能体，LLM 自主决策工具调用
- **调用链追踪**：完整的工具调用路径追踪和可视化

## 项目结构

```
├── .claude/
│   ├── agents/              # AI 团队角色定义
│   │   ├── pm.md            # 产品经理
│   │   ├── project_manager.md # 项目经理
│   │   ├── architect.md     # 架构师
│   │   ├── developer.md     # 开发者
│   │   ├── tester.md        # 测试工程师
│   │   └── reviewer.md      # 代码审查者
│   └── shared/              # 团队共享资源
│       ├── inbox/           # 收件箱（按角色）
│       ├── outbox/          # 发件箱（按角色）
│       └── knowledge/       # 知识库
│
├── adapters/                # 适配器模块
│   ├── core/                # 核心框架
│   │   ├── types.py         # 类型定义
│   │   ├── base_adapter.py  # 适配器基类
│   │   ├── adapter_factory.py # 适配器工厂
│   │   └── schema_validator.py # Schema 验证器
│   ├── http/                # HTTP/OpenAPI 适配器
│   │   ├── base.py
│   │   ├── client.py
│   │   └── openapi_parser.py
│   ├── mcp/                 # MCP 适配器
│   │   ├── base.py
│   │   ├── client.py
│   │   ├── transports.py
│   │   └── servers/         # MCP Server 实现
│   └── shell/               # Shell 适配器
│       ├── base.py
│       ├── sandbox.py
│       └── executor.py
│
├── skills/                  # Skill 仓库（标准格式）
│   ├── _skill-template/     # Skill 模板
│   ├── http-example-skill/  # HTTP 适配器示例
│   ├── mcp-example-skill/   # MCP 适配器示例
│   ├── shell-example-skill/ # Shell 适配器示例
│   └── sqlite-query-skill/  # SQLite 查询技能
│
├── subagents/               # SubAgent 仓库（自动扫描）
│   ├── _subagent-template/  # Agent 模板
│   ├── code-analyzer/       # 代码分析 Agent
│   └── web-scraper/         # 网页抓取 Agent
│
├── .claude/                 # Claude 配置
│   ├── agents/              # AI 团队角色定义
│   ├── shared/              # 团队共享资源
│   ├── mcp.json             # MCP 服务器配置
│   └── README.md            # 配置说明
│
├── spec/
│   ├── Me2AI/               # 用户维护的设计文档
│   │   ├── 功能需求描述.md
│   │   ├── 非功能需求描述.md
│   │   ├── 技术约束.md
│   │   └── 任务规划.md
│   └── AI2AI/               # AI 维护的代码状态总结
│       ├── 架构设计.md
│       ├── 接口规范.md
│       ├── Skills模块说明.md
│       └── 适配器模块说明.md
│
├── config/
│   ├── skills.yaml          # Skill 配置
│   └── adapters.yaml        # 适配器配置
│
├── src/
│   ├── llm_client.py        # LLM 客户端
│   ├── skill_loader.py      # Skill 资源加载器
│   ├── skill_executor.py    # Skill 执行器
│   ├── intent/              # 意图识别模块
│   │   └── recognizer.py
│   ├── mcp/                 # MCP 模块 ⭐
│   │   ├── config.py        # 配置加载器（Claude Code 标准）
│   │   ├── client.py        # MCP 客户端
│   │   └── transport/       # 传输层
│   │       ├── stdio.py     # STDIO 传输
│   │       └── http.py      # HTTP 传输
│   ├── subagent/            # SubAgent 模块 ⭐
│   │   ├── config.py        # 目录扫描器
│   │   ├── base_agent.py    # Agent 基类
│   │   └── orchestrator.py  # 编排器
│   ├── agent/               # Agent 模块
│   │   └── stream_agent.py  # 流式 Agent
│   ├── memory/              # 记忆模块
│   └── web/                 # Web 模块
│
├── static/                  # 静态资源
│   ├── index.html           # Web 界面
│   ├── css/style.css        # 样式
│   └── js/
│       ├── app.js           # 主应用
│       ├── chat.js          # 聊天逻辑
│       └── memory.js        # localStorage 管理
│
├── data/                    # 数据目录
│   ├── test.db              # SQLite 测试数据库
│   └── init_db.py           # 数据库初始化脚本
│
├── tasks/
│   ├── pending/             # 待处理任务
│   ├── in_progress/         # 进行中任务
│   └── completed/           # 已完成任务
│
└── script/
    └── start_team.bat       # 启动脚本
```

---

## 快速开始

### 1. 环境要求

```
- Python 3.10+
- Claude Code CLI
- Git
```

### 2. 安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 可选：MCP 相关
pip install mcp
```

### 3. 启动 Web 服务

```bash
# 方式 1：运行启动脚本
script/start-web.bat

# 方式 2：直接运行
python -m src.web.main

# 方式 3：使用 uvicorn
uvicorn src.web.main:app --host 0.0.0.0 --port 8000 --reload
```

服务启动后访问：
- **Web 界面**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs

### 4. 启动团队协作模式

```bash
# 在 Claude Code 中执行
/team-dev        # 初始化团队环境
/start-flow 你的项目名  # 启动工作流
```

---

## Web 界面

### 功能特性

- **流式对话**: SSE 批量化 + requestAnimationFrame 渲染，丝滑无卡顿
- **完整 Markdown**: marked.js 渲染，支持代码块、表格、列表、标题等 GFM 语法
- **浏览器记忆**: 使用 localStorage 存储对话历史，刷新页面后自动恢复
- **短期记忆**: 后端自动总结长对话（超过 20 条消息时触发）
- **SQLite 查询**: 支持 SQLite 数据库查询的 Skill
- **停止生成**: 随时中断流式响应（AbortController）
- **智能滚动**: 用户上滚时不强制拉回底部

### API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/chat/stream` | POST | 流式聊天接口 (SSE) |
| `/api/chat/message` | POST | 非流式聊天接口 |
| `/api/session/{id}` | GET | 获取会话历史 |
| `/api/session/{id}` | DELETE | 清除会话 |
| `/api/session/{id}/summarize` | POST | 手动触发总结 |
| `/health` | GET | 健康检查 |

### SSE 响应格式

```
data: {"type": "start", "session_id": "xxx"}\n\n
data: {"type": "content", "content": "文本块"}\n\n
data: {"type": "summary", "message": "对话已自动总结"}\n\n
data: {"type": "done", "session_id": "xxx"}\n\n
```

### 前端文件结构

```
static/
├── index.html        # 聊天界面（含 marked.js CDN）
├── css/style.css     # 暗色主题 + 流式光标 + 平滑滚动
└── js/
    ├── app.js        # UI 控制器（智能滚动 + 停止按钮 + 事件委托）
    ├── chat.js       # 流式核心（rAF 批处理 + SSE 累积 + AbortController）
    └── memory.js     # localStorage 管理
```

### 前端流式架构

```
SSE chunk 到达 → 累积到 _pendingChunks（不碰 DOM）
               → _scheduleRender() 调度 rAF
               → rAF 回调：marked.js 渲染 → innerHTML（每帧最多 1 次）
               → 智能滚动（仅在用户位于底部时自动滚动）
```

---

## SQLite 查询 Skill

### 自动意图识别

系统现在支持**自动 Skill 匹配**：
1. 用户输入自动进行意图识别
2. 匹配到 Skill（置信度 >= 0.3）→ 执行 Skill 返回结果
3. 未匹配到 Skill → 降级到 LLM 生成响应

**示例**：
- 输入 "查询张三" → 自动触发 `sqlite-query-skill`
- 输入 "今天天气" → 无匹配，LLM 生成响应

### 初始化测试数据库

```bash
python data/init_db.py
```

这会创建 `data/test.db` 数据库，包含 10 条测试人员数据。

### 测试查询

在 Web 界面输入：
- "查询张三的信息" - 按姓名搜索
- "搜索技术部的员工" - 按部门搜索
- "列出所有人员" - 列出所有

### CLI 测试

```bash
python -c "
import sys
sys.path.insert(0, '.')
from skills.sqlite-query-skill.scripts.executor import execute
result = execute({'user_input': '查询张三'}, {})
print(result['response'])
"
```

---

## 创建新 Skill

### 1. 复制模板

```bash
# 复制模板目录
cp -r skills/_skill-template skills/my-new-skill
```

### 2. 编辑 SKILL.md

```yaml
---
# ==========================================
# 基础元数据（必需）
# ==========================================
name: my-new-skill
description: 我的技能描述
version: 1.0.0
author: your-name
tags: [tag1, tag2]

# ==========================================
# 分类与优先级
# ==========================================
tier: CORE              # CORE / POWERFUL / SPECIALIZED
category: general       # engineering / business / data
priority: 10

# ==========================================
# 意图与触发
# ==========================================
intents:
  - my_intent
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
# 输入输出 Schema
# ==========================================
input_schema:
  type: object
  properties:
    query:
      type: string
      description: 查询内容
  required: [query]

output_schema:
  type: object
  properties:
    result:
      type: string
    success:
      type: boolean

# ==========================================
# 执行配置
# ==========================================
execution:
  timeout: 30
  stream_enabled: true

# ==========================================
# 重试配置（可选）
# ==========================================
retry:
  max_attempts: 3
  strategy: exponential
  base_delay: 1.0

# ==========================================
# 降级配置（可选）
# ==========================================
fallback:
  strategy: llm_assist
  message: "服务暂时不可用"
---

# 技能指令

## 功能说明
这里是 Skill 的详细功能说明。

## 使用方法
...
```

### 3. 实现执行器

```python
# skills/my-new-skill/scripts/executor.py

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
    """Skill 执行器"""

    async def execute(self, context: SkillContext) -> SkillResult:
        """执行技能逻辑"""
        try:
            # 实现你的逻辑
            result = self._process(context.user_input)

            return SkillResult(
                success=True,
                response=f"处理完成: {result}",
                data={"input": context.user_input}
            )
        except Exception as e:
            return SkillResult(
                success=False,
                response="",
                error=str(e)
            )

    def _process(self, user_input: str) -> str:
        """处理逻辑"""
        return user_input.upper()
```

---

## 适配器使用指南

### 适配器类型对比

| 适配器类型 | 用途 | 协议/标准 | 适用场景 |
|-----------|------|----------|----------|
| Python | 执行内置脚本 | executor.py | 本地处理、复杂逻辑 |
| HTTP | 调用 REST API | OpenAPI 3.0 | 外部 API 集成 |
| MCP | 连接 MCP Server | Model Context Protocol | Claude MCP 生态 |
| Shell | 执行命令行工具 | POSIX Shell | DevOps、Git 操作 |

### 4.1 HTTP 适配器

**配置文件** (`config/adapters.yaml`)：

```yaml
http:
  my-api:
    base_url: https://api.example.com
    openapi_path: adapters/http/specs/my-api.yaml
    auth:
      type: bearer
      token_env: MY_API_TOKEN
    retry:
      max_retries: 3
      retry_status_codes: [429, 500, 502, 503, 504]
    health_url: /health
```

**代码使用**：

```python
from adapters import AdapterFactory, AdapterType, AdapterConfig
from adapters.core import SkillContext

# 创建适配器
config = AdapterConfig(
    type=AdapterType.HTTP,
    name="my-api",
    metadata={
        "base_url": "https://api.example.com",
        "openapi_path": "adapters/http/specs/my-api.yaml",
        "auth": {"type": "bearer", "token_env": "API_TOKEN"}
    }
)
adapter = AdapterFactory.create(config)
await adapter.initialize()

# 方式1：通过 operation_id 调用（推荐）
result = await adapter.execute(
    context=SkillContext(session_id="1", user_input="", intent=""),
    input_data={"operation_id": "getUser", "userId": "123"}
)

# 方式2：直接指定端点
result = await adapter.execute(
    context=SkillContext(session_id="1", user_input="", intent=""),
    input_data={"endpoint": "/users/123", "method": "GET"}
)

# 获取端点列表
endpoints = adapter.get_endpoints()
for ep in endpoints:
    print(f"{ep['method']} {ep['path']} - {ep['summary']}")

# 生成工具清单（用于 MCP）
manifest = adapter.get_tool_manifest()
```

**认证方式**：

| 类型 | 配置 | 说明 |
|------|------|------|
| Bearer | `type: bearer, token_env: TOKEN_VAR` | 从环境变量读取 Token |
| API Key | `type: api_key, key_env: KEY_VAR, header: X-API-Key` | 自定义 Header |
| Basic | `type: basic, username: user, password: pass` | Basic 认证 |

### 4.2 MCP 适配器

**传输方式**：

| 传输类型 | 场景 | 说明 |
|---------|------|------|
| stdio | 本地进程 | 标准 MCP 传输方式 |
| sse | 远程服务 | Server-Sent Events |
| streamable-http | 远程服务 | 可流式 HTTP |

**代码使用**：

```python
from adapters.mcp import MCPClient

# stdio 传输（本地进程）
async with MCPClient(
    transport_type="stdio",
    transport_config={"server_path": "adapters/mcp/servers/echo/server.py"}
) as client:
    # 列出工具
    tools = await client.list_tools()
    for tool in tools:
        print(f"- {tool.name}: {tool.description}")

    # 调用工具
    result = await client.call_tool("echo", {"message": "Hello!"})
    print(result)  # [{"type": "text", "text": "Echo: Hello!"}]

    # 访问资源
    resources = await client.list_resources()
    content = await client.read_resource("file:///path/to/file")

    # 获取提示词
    prompts = await client.list_prompts()
    prompt = await client.get_prompt("example_prompt", {"arg": "value"})
```

**配置文件** (`config/adapters.yaml`)：

```yaml
mcp:
  echo-server:
    server_path: adapters/mcp/servers/echo/server.py
    transport: stdio

  remote-server:
    server_url: https://mcp-server.example.com/sse
    transport: sse
    headers:
      Authorization: Bearer ${MCP_TOKEN}
```

### 4.3 Shell 适配器

**安全机制**：

- 命令白名单：只有允许的命令可以执行
- 危险命令检测：正则表达式检测危险模式
- 资源限制：CPU、内存、超时控制
- 沙箱模式：禁止写入操作

**代码使用**：

```python
from adapters.shell import create_executor, ShellAdapter

# 创建执行器
executor = create_executor(
    work_dir="/project",
    allowed_commands={"git", "npm", "pip", "python"}
)

# 验证命令（不执行）
is_valid, error = executor.validate("git status")
if not is_valid:
    print(f"命令不安全: {error}")

# 执行命令
result = await executor.execute("git status", timeout=30)
if result.success:
    print(result.stdout)
else:
    print(f"执行失败: {result.error}")

# 批量执行
results = await executor.execute_batch(
    ["git status", "git log --oneline -5"],
    parallel=False
)
```

**配置文件** (`config/adapters.yaml`)：

```yaml
shell:
  git-tools:
    work_dir: ${PROJECT_ROOT}
    sandbox: true
    allowed_commands:
      - git
      - npm
      - pip
    timeout: 60

  docker-tools:
    work_dir: ${PROJECT_ROOT}
    sandbox: true
    allowed_commands:
      - docker
      - docker-compose
```

**默认允许的命令**：

```
git, svn, npm, yarn, pnpm, pip, pip3, python, python3,
node, deno, go, docker, kubectl, helm, terraform,
ls, cat, grep, find, curl, wget
```

**默认禁止的命令**：

```
rm -rf /, mkfs, sudo, chmod 777, dd, iptables, nc -l
```

---

## Skill 目录结构说明

```
skill-name/
├── SKILL.md              # 核心指令 + YAML 元数据（必需）
├── templates/            # 常用模板（Claude 按需读取）
│   ├── response.md
│   └── format.md
├── examples/             # 优秀/反例（给 Claude 看标准）
│   ├── good-example.md
│   └── anti-pattern.md
├── references/           # 规范、规则、禁用词表
│   ├── api-spec.md
│   └── conventions.md
└── scripts/              # 可执行脚本
    └── executor.py
```

| 目录 | 必需 | 用途 |
|------|------|------|
| `SKILL.md` | ✅ | 核心指令 + YAML Front Matter 元数据 |
| `templates/` | 可选 | 常用模板，Claude 按需读取 |
| `examples/` | 可选 | 优秀示例和反例，给 Claude 看标准 |
| `references/` | 可选 | 规范、规则、禁用词表等参考文档 |
| `scripts/` | 可选 | 可执行脚本（需开启 code execution）|

---

## 团队协作模式

### 可用角色

| 角色 | 职责 |
|------|------|
| PM (产品经理) | 需求收集、PRD编写、协调团队 |
| 项目经理 | 任务分解、分配、进度跟踪 |
| 架构师 | 系统架构设计、技术选型 |
| 开发者 | 编码实现、单元测试 |
| 测试工程师 | 测试用例、质量保证 |
| 代码审查者 | 代码审查、最佳实践 |

### 工作流程

```
用户 ──对话──> PM ──PRD──> 项目经理 ──任务──> 架构师
                                              │
                                              ▼
审查者 <──代码── 开发者 <──设计── 架构师
   │
   ▼
测试 ──验证──> 完成
```

### 常用命令

```bash
# 初始化团队环境
/team-dev

# 启动工作流
/start-flow 我的电商系统

# 查看任务列表
/tasks

# 提交代码
/commit
```

---

## Spec 驱动开发

本项目采用 Spec 驱动 AI 编码的开发方式：

### Me2AI 层 (`spec/Me2AI/`)

用户维护的设计意图与技术约束：

- `功能需求描述.md` - 功能需求细节
- `非功能需求描述.md` - 非功能需求
- `技术约束.md` - 架构和技术栈要求
- `任务规划.md` - 任务规划

### AI2AI 层 (`spec/AI2AI/`)

AI 维护的代码状态结构化总结：

- `架构设计.md` - 系统架构设计
- `接口规范.md` - API 接口规范
- `Skills模块说明.md` - Skills 模块文档
- `适配器模块说明.md` - 适配器模块文档

---

## 配置文件

### adapters.yaml

```yaml
# config/adapters.yaml

# 全局配置
global:
  enabled: true
  default_timeout: 30

# HTTP 适配器配置
http:
  order-api:
    base_url: https://api.example.com
    openapi_path: adapters/http/specs/order-api.yaml
    auth:
      type: bearer
      token_env: ORDER_API_TOKEN
    retry:
      max_retries: 3
    health_url: /health

# MCP 适配器配置
mcp:
  echo-server:
    server_path: adapters/mcp/servers/echo/server.py
    transport: stdio

# Shell 适配器配置
shell:
  git-tools:
    work_dir: ${PROJECT_ROOT}
    sandbox: true
    allowed_commands: [git, npm, pip]
```

### skills.yaml

```yaml
# config/skills.yaml

global:
  enabled: true
  hot_reload: true
  default_timeout: 30

# 快捷操作
quick_actions:
  order-assistant:
    - label: "[ORDER] 订单查询"
      message: "查询订单 12345678"
```

---

## 参考项目

| 项目 | 说明 |
|------|------|
| [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | 192+ Skills 标准格式 |
| [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) | 官方 MCP 服务器 |
| [encode/httpx](https://github.com/encode/httpx) | 异步 HTTP 客户端 |
| [faif/python-patterns](https://github.com/faif/python-patterns) | Python 设计模式 |

---

## MCP 和 SubAgent 模块

### MCP 模块

**功能**: 兼容 Claude Code 的 MCP (Model Context Protocol) 配置和客户端

**配置文件**: `.claude/mcp.json`

**核心组件**:
- `src/mcp/config.py` - 配置加载器（支持用户级和项目级配置）
- `src/mcp/client.py` - MCP 客户端（管理所有服务器连接）
- `src/mcp/transport/stdio.py` - STDIO 传输（本地进程）
- `src/mcp/transport/http.py` - HTTP 传输（远程服务）

**使用示例**:
```python
from mcp import MCPClient

# 创建客户端
client = MCPClient()
await client.initialize()

# 调用工具
result = await client.call_tool("filesystem", "read_file", {"path": "./test.txt"})

# 列出工具
tools = await client.list_tools("filesystem")

# 关闭连接
await client.shutdown()
```

**传输方式**:
- **STDIO**: 启动本地 MCP Server 进程，通过 stdin/stdout 通信
- **HTTP**: 通过 HTTP 协议连接远程 MCP Server

### SubAgent 模块

**功能**: 支持多 Agent 协作的编排系统

**自动发现**: 扫描 `subagents/` 目录（项目根目录下，与 `skills/` 平级），无需手动注册

**⚠️ 重要**: `subagents/` 目录必须位于项目根目录下，与 `skills/` 目录平级。
- `src/subagent/config.py` - 目录扫描器和加载器
- `src/subagent/base_agent.py` - Agent 基类
- `src/subagent/orchestrator.py` - 编排器（路由、并行执行、链式调用）

**目录结构**:
```
subagents/                  # 与 skills 平级
├── _subagent-template/     # Agent 模板
├── code-analyzer/          # 代码分析 Agent
└── web-scraper/            # 网页抓取 Agent
```

**使用示例**:
```python
from subagent import SubAgentOrchestrator, SubAgentInput

# 创建编排器
orchestrator = SubAgentOrchestrator()
await orchestrator.initialize()

# 路由到最合适的 Agent
input_data = SubAgentInput(query="分析这段代码")
result = await orchestrator.route(input_data)

# 并行执行多个 Agents
results = await orchestrator.route_parallel(input_data, max_agents=3)

# 链式调用
result = await orchestrator.chain(input_data, ["agent1", "agent2"])

# 关闭编排器
await orchestrator.shutdown()
```

**执行模式**:
- **路由**: 基于置信度选择最合适的 Agent
- **并行**: 同时执行多个 Agent 进行多角度分析
- **链式**: 按顺序执行多个 Agent，前一个的输出作为后一个的输入

### 测试

运行快速测试脚本:
```bash
python scripts/test_mcp_subagent.py
```

查看详细测试报告:
- `docs/test_report_mcp_subagent.md` - 完整测试报告
- `docs/test_issues_fix_plan.md` - 问题修复计划

---

## Agentic 架构

### 核心: Agent Loop（参考 OpenClaw 原理）

系统采用 Agentic Loop 架构，LLM 自主决策工具调用并支持多轮迭代：

```
用户输入 → StreamAgent.chat_stream()
    ↓
1. 构建 messages
   - system prompt（含 Skill 上下文注入）
   - 对话历史
   - 用户输入
    ↓
2. Agent Loop (while iteration < max_iterations):
   ├─ 调用 LLM（带 tools 参数）
   ├─ 如果返回 tool_calls:
   │   ├─ 实时流式输出工具调用过程
   │   ├─ AdapterFactory 执行工具
   │   ├─ 追加结果到 messages
   │   └─ 继续循环（让 LLM 看到结果后决定下一步）
   └─ 如果无 tool_calls:
       └─ 输出最终回答，退出循环
    ↓
3. 追加调用链签名 + 保存记忆
```

**关键特性**：
- **多轮迭代**：LLM 调用工具后能看到结果，并决定是否继续调用
- **Skill Context 注入**：SKILL.md 正文注入系统提示词（双重驱动）
- **实时流式**：每轮工具调用过程实时推送给前端
- **Hook Points**：`before/after_model_call`、`before/after_tool_calls`、`on_loop_start/end`
- **安全限制**：`max_iterations`（默认 10）防止无限循环

### 工具注册表

所有工具（Skills/MCP/SubAgent/Custom）统一注册到 ToolRegistry：

```python
from src.agent.tool_registry import get_global_registry

registry = get_global_registry()

# 注册自定义工具
@registry.register("my_tool", description="My custom tool")
def my_function(param1: str) -> str:
    return f"Hello {param1}"

# 生成 OpenAPI Schema（用于 LLM Function Calling）
schema = registry.to_openapi_schema()
```

### 适配器工厂

AdapterFactory 负责路由工具调用到正确的适配器：

```python
from src.adapters import get_global_factory

factory = get_global_factory()
await factory.initialize()

# 自动路由到正确的适配器
response = await factory.route(
    tool_name="sqlite:query",
    parameters={"sql": "SELECT * FROM users"},
    session_id="session_123"
)
```

### 调用链追踪

ChainTracker 自动追踪工具调用路径，并在响应末尾添加签名：

```
[LLM]
[tool: sqlite:query]
[tool: code-analyzer]
```

---

*文档更新时间: 2026-04-29*

大哥，请阅！
