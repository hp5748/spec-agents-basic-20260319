# 项目配置说明

## MCP 服务器

本项目支持 MCP (Model Context Protocol) 服务器，配置文件位于 `.claude/mcp.json`。

### 配置的服务器

| 名称 | 描述 | 状态 |
|------|------|------|
| filesystem | 本地文件系统访问 | 🔧 需启用 |
| sqlite | SQLite 数据库 | 🔧 需启用 |
| github | GitHub 集成 | 🔧 需配置 token |

### 启用服务器

编辑 `.claude/mcp.json`，将 `"disabled": true` 改为 `"disabled": false`。

### 环境变量

需要配置的环境变量（在 `.env` 文件中）：

```bash
# GitHub MCP 需要的 Token
GITHUB_TOKEN=your_github_personal_access_token
```

---

## SubAgents

本项目支持 SubAgent（多 Agent 协作），通过扫描 `subagents/` 目录自动发现。

### 目录结构

```
subagents/                  # SubAgent 根目录（与 skills 平级）
├── _subagent-template/     # Agent 模板
│   ├── agent.py            # Agent 实现文件
│   ├── AGENT.md            # Agent 描述文档
│   └── prompts/
│       └── system.md       # 系统提示词
│
├── code-analyzer/          # 代码分析 Agent（示例）
│   ├── agent.py
│   └── prompts/
│       └── system.md
│
└── web-scraper/            # 网页抓取 Agent（示例）
    ├── agent.py
    └── prompts/
        └── system.md
```

### 创建新 SubAgent

1. 复制模板：`cp -r subagents/_subagent-template subagents/my-agent`
2. 编辑 `agent.py` 实现 Agent 类
3. （可选）添加 `AGENT.md` 描述文档
4. 系统会自动发现并加载

### Agent 实现示例

```python
# subagents/my-agent/agent.py
from src.subagent import SubAgent, SubAgentInput, SubAgentOutput, AgentConfig

class Agent(SubAgent):
    def __init__(self, agent_id: str, config: AgentConfig, llm_client=None):
        super().__init__(agent_id, config, llm_client)
        self.set_system_prompt("你是XXX专家...")

    async def process(self, input_data: SubAgentInput) -> SubAgentOutput:
        # 处理逻辑
        return SubAgentOutput(
            success=True,
            response="处理结果",
            data={}
        )

    def can_handle(self, input_data: SubAgentInput) -> float:
        # 评估置信度
        if "关键词" in input_data.query:
            return 0.8
        return 0.0
```

---

## 配置文件格式

### MCP 配置 (.claude/mcp.json)

```json
{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-xxx"],
      "env": {"VAR": "$VAR"},
      "disabled": false
    }
  }
}
```

---

## 参考文档

- [Claude Code MCP 完全指南](https://github.com/datawhalechina/easy-vibe/blob/main/docs/zh-cn/stage-3/core-skills/mcp/index.md)
- [MCP 规范](https://spec.modelcontextprotocol.io/)
