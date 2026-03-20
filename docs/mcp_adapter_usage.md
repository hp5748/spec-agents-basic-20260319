# MCP Adapter 使用指南

## 概述

MCP Adapter 是对原 MCP 模块的迁移，符合 Adapter 接口规范，支持多种配置格式和传输方式。

## 主要特性

- **多格式配置支持**：
  - `config/mcp.yaml` - 项目 YAML 配置（最高优先级）
  - `.claude/mcp.json` - Claude Code 标准格式
  - `register/mcp.json` - 注册中心配置
  - `~/.claude.json` - 用户级配置

- **多传输方式**：
  - STDIO 传输（本地进程）
  - HTTP 传输（远程服务）
  - SSE 传输（服务器推送事件）

- **自动工具注册**：MCP 服务器的工具自动注册到 ToolRegistry

## 基本使用

### 1. 配置 MCP 服务器

创建 `config/mcp.yaml`：

```yaml
mcp_servers:
  # SQLite MCP 示例
  sqlite:
    enabled: true
    transport: stdio
    command: uvx
    args:
      - "--no-cache"
      - "mcp-server-sqlite"
      - "--db-path"
      - "data/users.db"
    env: {}

  # HTTP MCP 示例
  remote-service:
    enabled: true
    transport: http
    url: "http://localhost:8080/mcp"
    headers:
      Authorization: "Bearer token123"
```

### 2. 创建 MCP Adapter

```python
from src.adapters.mcp import MCPAdapter
from src.adapters.core import AdapterConfig, AdapterType

# 创建适配器配置
config = AdapterConfig(
    type=AdapterType.MCP,
    name="my_mcp_adapter",
    metadata={"project_root": "."}
)

# 创建并初始化适配器
adapter = MCPAdapter(config)
await adapter.initialize()
```

### 3. 调用 MCP 工具

```python
from src.adapters.core import ToolRequest

# 创建工具请求
request = ToolRequest(
    tool_name="sqlite:query",  # 格式：server_name:tool_name
    parameters={"sql": "SELECT * FROM users"}
)

# 执行工具调用
response = await adapter.execute(request)

if response.success:
    print(f"执行成功: {response.data}")
else:
    print(f"执行失败: {response.error}")
```

### 4. 列出可用工具

```python
# 列出所有工具
tools = await adapter.list_tools()
for tool in tools:
    print(f"可用工具: {tool}")

# 获取适配器能力
capabilities = adapter.get_capabilities()
print(f"支持流式: {capabilities.supports_streaming}")
print(f"支持批量: {capabilities.supports_batch}")
print(f"可用工具数: {len(capabilities.tools)}")
```

## 高级使用

### 使用工厂模式

```python
from src.adapters.core import AdapterFactory, AdapterConfig, AdapterType

# 创建工厂
factory = AdapterFactory()

# 创建配置
config = AdapterConfig(
    type=AdapterType.MCP,
    name="mcp_adapter",
    metadata={"project_root": "."}
)

# 通过工厂创建适配器
adapter = await factory.create_adapter(config)

# 路由工具调用
response = await factory.route(
    tool_name="sqlite:query",
    parameters={"sql": "SELECT * FROM users"}
)
```

### 使用适配器管理器

```python
from src.adapter_manager import AdapterManager

# 初始化管理器
manager = AdapterManager("config/adapters.yaml")
await manager.initialize()

# 获取适配器
adapter = manager.get_adapter("mcp_adapter")

# 执行工具调用
response = await adapter.execute(request)

# 清理
await manager.cleanup()
```

## 配置格式示例

### YAML 格式（推荐）

```yaml
# config/mcp.yaml
mcp_servers:
  filesystem:
    enabled: true
    transport: stdio
    command: npx
    args:
      - "-y"
      - "@modelcontextprotocol/server-filesystem"
      - "/path/to/allowed/directory"

  brave-search:
    enabled: true
    transport: stdio
    command: uvx
    args:
      - "--no-cache"
      - "mcp-brave-search"
    env:
      BRAVE_API_KEY: "$BRAVE_API_KEY"
```

### JSON 格式（兼容 Claude Code）

```json
// .claude/mcp.json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"]
    },
    "brave-search": {
      "command": "uvx",
      "args": ["--no-cache", "mcp-brave-search"],
      "env": {
        "BRAVE_API_KEY": "$BRAVE_API_KEY"
      }
    }
  }
}
```

## 工具命名规范

MCP Adapter 使用以下工具命名格式：

```
{server_name}:{tool_name}
```

例如：
- `sqlite:query`
- `filesystem:read_file`
- `brave-search:search`

## 错误处理

```python
try:
    response = await adapter.execute(request)
    if response.success:
        # 处理成功响应
        data = response.data
    else:
        # 处理错误
        error = response.error
        print(f"工具调用失败: {error}")
except Exception as e:
    print(f"执行异常: {e}")
```

## 健康检查

```python
# 检查适配器健康状态
status = await adapter.health_check()

if status.healthy:
    print(f"适配器健康: {status.message}")
else:
    print(f"适配器不健康: {status.message}")

# 查看详细信息
print(f"连接的服务器数: {status.metadata.get('connected_servers', 0)}")
print(f"可用工具数: {status.metadata.get('total_tools', 0)}")
```

## 清理资源

```python
# 关闭适配器
await adapter.shutdown()

# 或使用工厂关闭所有适配器
await factory.shutdown_all()
```

## 迁移指南

如果从旧版 MCP 模块迁移：

```python
# 旧代码
from src.mcp import MCPClient

client = MCPClient()
await client.initialize()
result = await client.call_tool("server", "tool", {})

# 新代码
from src.adapters.mcp import MCPAdapter
from src.adapters.core import AdapterConfig, AdapterType, ToolRequest

adapter = MCPAdapter(AdapterConfig(
    type=AdapterType.MCP,
    name="mcp_adapter",
    metadata={"project_root": "."}
))
await adapter.initialize()

request = ToolRequest(
    tool_name="server:tool",  # 注意命名格式变化
    parameters={}
)
response = await adapter.execute(request)
```

## 注意事项

1. **工具命名**：MCP 工具名格式为 `server_name:tool_name`
2. **配置优先级**：YAML > register > JSON > user
3. **环境变量**：使用 `$VAR_NAME` 格式引用环境变量
4. **异步操作**：所有操作都是异步的，需要使用 `await`
5. **资源清理**：使用完毕后记得调用 `shutdown()` 释放资源

## 测试

运行测试：

```bash
# 单元测试
pytest tests/test_mcp_adapter.py -v

# 集成测试
python -m tests.test_mcp_integration
```
