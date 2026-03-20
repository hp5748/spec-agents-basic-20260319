# SubAgent 模块说明

## 概述

SubAgent 模块实现多 Agent 协作能力，支持任务路由、并行执行和链式调用。

**与 MCP 的区别**：
- **MCP**: 连接外部服务器（需要启动进程），需要 JSON 配置
- **SubAgent**: 内部 Python 类（无需进程），通过扫描目录自动发现

### 当前状态

| 功能 | 状态 | 说明 |
|------|------|------|
| 目录扫描 | ✅ 已实现 | 自动发现 subagents/ 目录下的 Agent |
| Agent 基类 | ✅ 已实现 | `src/subagent/base_agent.py` |
| 编排器 | ✅ 已实现 | `src/subagent/orchestrator.py` |
| StreamAgent 集成 | ⏳ 待实现 | 需要修改 `src/agent/stream_agent.py` |

---

## 目录结构

```
subagents/                              # SubAgent 根目录（与 skills 平级）
├── _subagent-template/                 # Agent 模板
│   ├── agent.py                        # Agent 实现文件
│   ├── AGENT.md                        # Agent 描述文档（可选）
│   └── prompts/
│       └── system.md                   # 系统提示词（可选）
│
├── code-analyzer/                      # 代码分析 Agent
│   ├── agent.py
│   ├── AGENT.md
│   └── prompts/
│       └── system.md
│
└── web-scraper/                        # 网页抓取 Agent
    ├── agent.py
    ├── AGENT.md
    └── prompts/
        └── system.md
```

---

## 核心 API

### SubAgentScanner

```python
from src.subagent import SubAgentScanner

scanner = SubAgentScanner()
agents = scanner.scan()
# 返回: {"agent-name": DiscoveredAgent(...)}
```

### SubAgentOrchestrator

```python
from src.subagent import SubAgentOrchestrator, SubAgentInput

# 初始化
orchestrator = SubAgentOrchestrator()
await orchestrator.initialize()

# 路由到最合适的 Agent
input_data = SubAgentInput(query="分析这段代码")
result = await orchestrator.route(input_data)

# 并行执行多个 Agents
results = await orchestrator.route_parallel(input_data, max_agents=3)

# 链式调用
result = await orchestrator.chain(input_data, ["agent1", "agent2"])

# 流式路由
async for chunk in orchestrator.route_stream(input_data):
    print(chunk, end="")
```

---

## 实现 SubAgent

### 基本结构

```python
# subagents/my-agent/agent.py
from src.subagent import SubAgent, SubAgentInput, SubAgentOutput, AgentConfig

class Agent(SubAgent):
    """
    我的 Agent

    在 AGENT.md 中添加详细描述。
    """

    def __init__(self, agent_id: str, config: AgentConfig, llm_client=None):
        super().__init__(agent_id, config, llm_client)

        # 设置系统提示词（可选）
        self.set_system_prompt("你是XXX专家...")

    async def process(self, input_data: SubAgentInput) -> SubAgentOutput:
        """
        处理输入并返回输出
        """
        try:
            # 实现你的逻辑
            result = await self._do_something(input_data.query)

            return SubAgentOutput(
                success=True,
                response=f"处理完成: {result}",
                data={"input": input_data.query}
            )
        except Exception as e:
            return SubAgentOutput(
                success=False,
                response="",
                error=str(e)
            )

    def can_handle(self, input_data: SubAgentInput) -> float:
        """
        判断是否能处理此输入

        返回置信度 0.0-1.0
        """
        # 方法1: 关键词匹配
        keywords = ["分析", "检查", "review", "analyze"]
        for kw in keywords:
            if kw in input_data.query:
                return 0.8

        # 方法2: LLM 判断（如果有 llm_client）
        # if self._llm_client:
        #     # 使用 LLM 判断...
        #     pass

        return 0.0

    async def _do_something(self, query: str) -> str:
        """实际处理逻辑"""
        return query.upper()
```

### AGENT.md 模板

```markdown
# 代码分析 Agent

## 描述

专门负责代码分析、问题检测和模式识别的 Agent。

## 能力

- 代码审查
- 问题检测
- 模式识别
- 最佳实践建议

## 触发关键词

- 代码分析
- 检查代码
- code review
- analyze code

## 使用示例

```
用户: 分析这段代码
Agent: [开始分析...]
```
```

---

## 编排模式

### 1. 路由模式 (route)

选择最合适的 Agent 执行任务。

```python
result = await orchestrator.route(input_data)
```

### 2. 并行模式 (route_parallel)

多个 Agent 并行执行，获取多个视角的结果。

```python
results = await orchestrator.route_parallel(input_data, max_agents=3)
```

### 3. 链式模式 (chain)

依次调用多个 Agent，前一个的输出作为下一个的输入。

```python
result = await orchestrator.chain(input_data, ["analyzer", "reviewer"])
```

---

## 源码结构

```
src/subagent/
├── __init__.py                       # 模块入口
├── config.py                         # 扫描器和加载器
├── base_agent.py                     # Agent 基类
└── orchestrator.py                   # 编排器
```

---

## 自动发现机制

SubAgent 通过以下方式自动发现：

1. 扫描 `subagents/` 目录
2. 查找每个子目录下的 `agent.py` 文件
3. 检查是否包含 `Agent` 类
4. 读取 `AGENT.md` 或 `prompts/system.md` 获取描述
5. 自动加载并初始化

**无需手动注册**！

---

*文档更新时间: 2026-03-19*
