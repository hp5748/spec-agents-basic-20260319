# MCP 模块说明

## 概述

MCP (Model Context Protocol) 模块使系统能够连接外部 MCP 服务器，扩展 Agent 的能力。

### 当前状态

| 功能 | 状态 | 说明 |
|------|------|------|
| 配置加载器 | ✅ 已实现 | `src/mcp/config.py` 支持 YAML/JSON |
| STDIO 传输 | ✅ 已实现 | `src/mcp/transport/stdio.py` |
| HTTP 传输 | ✅ 已实现 | `src/mcp/transport/http.py` |
| MCP 客户端 | ✅ 已实现 | `src/mcp/client.py` |
| 工具匹配器 | ✅ 已实现 | `src/mcp/tool_matcher.py` |
| StreamAgent 集成 | ✅ 已实现 | 统一路由：Skill → SubAgent → MCP → LLM |

---

## 配置方式

### 配置优先级

| 优先级 | 文件 | 格式 | 作用范围 |
|--------|------|------|----------|
| 1（最高） | `config/mcp.yaml` | YAML | 项目自定义 |
| 2 | `.claude/mcp.json` | JSON | Claude Code 标准 |
| 3（最低） | `~/.claude.json` | JSON | 用户级 |

### config/mcp.yaml 格式（推荐）

```yaml
# MCP 服务器配置
mcp_servers:
  # 文件系统操作
  filesystem:
    enabled: false  # 默认禁用
    transport: stdio
    command: npx
    args:
      - "-y"
      - "@modelcontextprotocol/server-filesystem"
      - "/allowed/path"
    env: {}

  # HTTP 请求
  fetch:
    enabled: false
    transport: stdio
    command: npx
    args:
      - "-y"
      - "@modelcontextprotocol/server-fetch"

  # SQLite 数据库
  sqlite:
    enabled: true
    transport: stdio
    command: uvx
    args:
      - "--no-cache"
      - "mcp-server-sqlite"
      - "--db-path"
      - "data/users.db"
```

### .claude/mcp.json 格式（Claude Code 标准）

### 配置文件位置

| 级别 | 路径 | 作用范围 |
|------|------|---------|
| 用户级 | `~/.claude.json` | 所有项目 |
| 项目级 | `.claude/mcp.json` | 当前项目 |

### 配置格式

```json
{
  "$schema": "https://json.schemastore.org/claude-mcp.json",
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "./data"],
      "env": {"VAR": "$VALUE"},
      "disabled": false
    },
    "remote-api": {
      "url": "https://api.example.com/mcp",
      "transport": "http",
      "headers": {
        "Authorization": "Bearer $TOKEN"
      }
    }
  }
}
```

---

## 核心数据类

### MCPServerConfig

```python
@dataclass
class MCPServerConfig:
    name: str
    transport: str = "stdio"           # stdio / http / sse
    command: Optional[str] = None      # STDIO 命令
    args: List[str] = []               # 命令参数
    url: Optional[str] = None          # HTTP URL
    headers: Dict[str, str] = {}       # HTTP 头
    env: Dict[str, str] = {}           # 环境变量
    disabled: bool = False             # 是否禁用
```

---

## 使用方式

### StreamAgent 自动路由

```python
from src.agent.stream_agent import StreamAgent

agent = StreamAgent(
    session_id="test",
    project_root="."
)

# 自动路由：Skill → SubAgent → MCP → LLM
response = await agent.chat("读取 README.md 文件")

# 响应会包含调用链签名：
# "文件内容...\n\n[MCP: filesystem]"
```

### MCPClient 直接调用

```python
from src.mcp import MCPClient

client = MCPClient(project_root=".")
await client.initialize()

# 调用工具
result = await client.call_tool(
    server_name="filesystem",
    tool_name="read_file",
    arguments={"path": "./test.txt"}
)

# 关闭
await client.shutdown()
```

### ToolMatcher 意图匹配

```python
from src.mcp import MCPClient, ToolMatcher

client = MCPClient()
await client.initialize()

matcher = ToolMatcher(client)
await matcher.initialize()

# 匹配用户输入到 MCP 工具
match = await matcher.match("帮我读取文件")
if match:
    # match.server_name, match.tool_name, match.arguments
    result = await client.call_tool(
        match.server_name,
        match.tool_name,
        match.arguments
    )
```

---

## 目录结构

```
src/mcp/
├── __init__.py                      # 模块入口
├── config.py                        # 配置加载器（支持 YAML）
├── client.py                        # MCP 客户端
├── tool_matcher.py                  # 工具意图匹配器
└── transport/
    ├── __init__.py
    ├── stdio.py                     # STDIO 传输
    └── http.py                      # HTTP 传输

config/
├── mcp.yaml                         # MCP YAML 配置（推荐）
└── adapters.yaml                    # 适配器模板（参考）
```

---

## 传输方式

### STDIO（本地进程）

```json
{
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-xxx", "--arg", "value"],
  "env": {"API_KEY": "$API_KEY"}
}
```

### HTTP（远程服务）

```json
{
  "url": "https://api.example.com/mcp",
  "transport": "http",
  "headers": {
    "Authorization": "Bearer $TOKEN"
  }
}
```

---

## 目录结构

```
src/mcp/
├── __init__.py                      # 模块入口
├── config.py                        # 配置加载器
├── client.py                        # MCP 客户端
└── transport/
    ├── __init__.py
    ├── stdio.py                     # STDIO 传输
    └── http.py                      # HTTP 传输
```

---

## 环境变量

支持 `$VAR` 语法自动展开环境变量：

```json
{
  "env": {
    "GITHUB_TOKEN": "$GITHUB_TOKEN",
    "DATABASE_URL": "$DATABASE_URL"
  }
}
```

---

*文档更新时间: 2026-03-20*
