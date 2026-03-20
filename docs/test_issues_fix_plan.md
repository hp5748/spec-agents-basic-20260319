# MCP 和 SubAgent 模块问题修复计划

**创建日期**: 2026-03-19
**优先级**: 高 → 中 → 低

---

## 高优先级问题 (建议立即修复)

### 1. HTTP 传输层的 ping 方法问题 ⚠️

**文件**: `src/mcp/transport/http.py` 第 49 行

**问题代码**:
```python
response = await self._client.post("/", json={"jsonrpc": "2.0", "method": "ping", "id": 1})
```

**问题分析**:
- MCP 协议中没有定义 `ping` 方法
- 这会导致连接测试时返回错误
- 可能导致某些 MCP 服务器无法连接

**修复方案**:
```python
# 方案 1: 使用 tools/list 进行连接测试
async def connect(self) -> None:
    """建立连接"""
    headers = {
        "Content-Type": "application/json",
        **self.config.headers
    }
    headers = self._expand_env_vars(headers)

    self._client = httpx.AsyncClient(
        base_url=self.config.url,
        headers=headers,
        timeout=self.config.env.get("timeout", 30)
    )

    # 测试连接 - 使用 tools/list 代替 ping
    try:
        response = await self._client.post("/", json={
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 1
        })
        if response.status_code == 200:
            self.config._status = "running"
            logger.info(f"MCP Server {self.config.name} 已连接")
    except Exception as e:
        logger.error(f"连接 MCP Server {self.config.name} 失败: {e}")
        self.config._status = "error"
        raise

# 方案 2: 简单的 HTTP 可达性测试
async def connect(self) -> None:
    """建立连接"""
    # ... 前面代码相同 ...

    # 简单测试服务器是否可达
    try:
        response = await self._client.get("/", timeout=5)
        # 只要服务器可达就认为连接成功
        self.config._status = "running"
        logger.info(f"MCP Server {self.config.name} 已连接")
    except Exception as e:
        logger.error(f"连接 MCP Server {self.config.name} 失败: {e}")
        self.config._status = "error"
        raise
```

**推荐**: 方案 1，更符合 MCP 协议规范

---

### 2. 异步任务未正确处理 ⚠️

**文件**: `src/mcp/transport/stdio.py` 第 58 行

**问题代码**:
```python
asyncio.create_task(self._read_responses())
```

**问题分析**:
- 创建的异步任务没有被保存
- 任务中的异常会被静默忽略
- 无法在 disconnect 时正确取消任务

**修复方案**:
```python
class STDIOTransport:
    def __init__(self, config: MCPServerConfig):
        self.config = config
        self._process: Optional[asyncio.subprocess.Process] = None
        self._request_id = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._read_task: Optional[asyncio.Task] = None  # 新增

    async def connect(self) -> None:
        """启动 MCP Server 进程"""
        # ... 前面代码相同 ...

        try:
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )

            # 启动响应监听任务并保存引用
            self._read_task = asyncio.create_task(self._read_responses())

            # 等待进程启动
            await asyncio.sleep(0.5)

            if self._process.returncode is not None:
                raise RuntimeError(f"MCP Server 启动失败，退出码: {self._process.returncode}")

            self.config._status = "running"
            logger.info(f"MCP Server {self.config.name} 已启动")

        except Exception as e:
            logger.error(f"启动 MCP Server {self.config.name} 失败: {e}")
            self.config._status = "error"
            raise

    async def disconnect(self) -> None:
        """断开连接"""
        if self._process:
            try:
                # 取消读取任务
                if self._read_task and not self._read_task.done():
                    self._read_task.cancel()
                    try:
                        await self._read_task
                    except asyncio.CancelledError:
                        pass

                # 终止进程
                self._process.terminate()
                await self._process.wait()
                logger.info(f"MCP Server {self.config.name} 已停止")
            except Exception as e:
                logger.error(f"停止 MCP Server {self.config.name} 失败: {e}")
            finally:
                self._process = None
                self._read_task = None
                self.config._status = "stopped"
```

---

## 中优先级问题 (建议近期修复)

### 3. 完善类型注解 ⚠️

**文件**:
- `src/mcp/transport/http.py`
- `src/subagent/base_agent.py`

**问题**:
```python
# http.py 第 27 行
from typing import Optional  # 缺少导入

# base_agent.py 第 72 行
from typing import Callable, Dict  # 缺少完整导入
```

**修复方案**:
```python
# src/mcp/transport/http.py
from typing import Any, Dict, List, Optional  # 确保导入 Optional

# src/subagent/base_agent.py
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional  # 确保导入所有需要的类型
```

---

### 4. 添加依赖检查 ⚠️

**文件**: `src/mcp/transport/http.py`

**问题**: HTTP 传输层依赖 `httpx`，但未在模块导入时检查

**修复方案**:
```python
"""
MCP HTTP 传输

通过 HTTP 协议与远程 MCP Server 通信。
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:
    raise ImportError(
        "httpx is required for HTTP transport. "
        "Install it with: pip install httpx"
    )

logger = logging.getLogger(__name__)
```

---

### 5. 提取魔法数字为配置 ⚠️

**文件**:
- `src/mcp/transport/stdio.py` 第 61 行
- `src/subagent/orchestrator.py` 第 101 行

**问题代码**:
```python
# stdio.py
await asyncio.sleep(0.5)  # 硬编码的等待时间

# orchestrator.py
if best_score < 0.3:  # 硬编码的置信度阈值
```

**修复方案**:

#### stdio.py
```python
@dataclass
class MCPServerConfig:
    """MCP Server 配置"""
    name: str
    transport: str = "stdio"
    command: Optional[str] = None
    args: List[str] = field(default_factory=list)
    url: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    env: Dict[str, str] = field(default_factory=dict)
    disabled: bool = False

    # 新增配置项
    startup_timeout: float = 0.5  # 进程启动等待时间

# 在 connect() 中使用
await asyncio.sleep(self.config.startup_timeout)
```

#### orchestrator.py
```python
class SubAgentOrchestrator:
    def __init__(
        self,
        project_root: str = ".",
        llm_client: Optional[Any] = None,
        confidence_threshold: float = 0.3  # 新增参数
    ):
        self._project_root = project_root
        self._llm_client = llm_client
        self._confidence_threshold = confidence_threshold
        # ... 其他代码 ...

    async def route(self, input_data: SubAgentInput) -> SubAgentOutput:
        # ... 前面代码 ...

        # 使用配置的阈值
        if best_score < self._confidence_threshold:
            return SubAgentOutput(
                success=False,
                response="没有合适的 Agent 可以处理此任务",
                error=f"最佳匹配分数: {best_score:.2f}"
            )
```

---

## 低优先级问题 (可以后续优化)

### 6. 统一环境变量展开逻辑 ⚠️

**问题**: 环境变量展开逻辑在多处重复

**影响位置**:
- `src/mcp/config.py` 第 116-123 行
- `src/mcp/transport/http.py` 第 66-76 行

**优化方案**:
```python
# 创建通用工具函数
# src/mcp/utils.py

import os
from typing import Any, Dict

def expand_env_vars(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    递归展开字典中的环境变量

    支持 $VAR 和 ${VAR} 格式
    """
    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            # 简单的 $VAR 格式
            if value.startswith("$"):
                var_name = value[1:]
                result[key] = os.getenv(var_name, value)
            # ${VAR} 格式
            elif value.startswith("${") and value.endswith("}"):
                var_name = value[2:-1]
                result[key] = os.getenv(var_name, value)
            else:
                result[key] = value
        elif isinstance(value, dict):
            result[key] = expand_env_vars(value)
        else:
            result[key] = value
    return result

# 在各处使用
# src/mcp/config.py
from .utils import expand_env_vars

def _parse_server_config(self, name: str, data: Dict[str, Any]) -> MCPServerConfig:
    env = expand_env_vars(data.get("env", {}))
    # ... 其他代码 ...
```

---

### 7. 改进错误日志 ⚠️

**建议**: 在关键位置添加更详细的错误日志

**示例**:
```python
# src/mcp/client.py
async def initialize(self) -> None:
    """初始化所有服务器连接"""
    self._config = self._loader.load()
    servers = self._config.get_all_servers()

    if not servers:
        logger.info("未配置 MCP 服务器")
        return

    logger.info(f"开始初始化 {len(servers)} 个 MCP 服务器...")

    # 并行连接所有服务器
    connection_tasks = []
    for name, server_config in servers.items():
        if server_config.disabled:
            logger.debug(f"服务器 {name} 已禁用，跳过")
            continue

        logger.debug(f"正在连接服务器: {name} ({server_config.transport})")
        connection_tasks.append((name, self._connect_server(name, server_config)))

    if connection_tasks:
        results = await asyncio.gather(
            *[task for _, task in connection_tasks],
            return_exceptions=True
        )

        for (name, _), result in zip(connection_tasks, results):
            if isinstance(result, Exception):
                logger.error(f"连接服务器 {name} 失败: {result}")
            else:
                logger.info(f"服务器 {name} 连接成功")

        success_count = sum(1 for r in results if not isinstance(r, Exception))
        logger.info(f"MCP 客户端初始化完成: {success_count}/{len(connection_tasks)} 个服务器已连接")
```

---

## 修复检查清单

### 高优先级
- [ ] 修复 HTTP 传输层的 ping 方法
- [ ] 修复异步任务处理问题

### 中优先级
- [ ] 完善类型注解
- [ ] 添加依赖检查
- [ ] 提取魔法数字为配置

### 低优先级
- [ ] 统一环境变量展开逻辑
- [ ] 改进错误日志

---

**创建日期**: 2026-03-19
**负责人**: 开发团队
**预计完成时间**: 高优先级 1-2 天，全部 1 周
