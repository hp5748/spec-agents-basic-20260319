"""
Shell 适配器

支持执行命令行工具，提供沙箱安全机制。

特性：
- 命令白名单/黑名单
- 危险命令检测
- 资源限制（CPU、内存、时间）
- 超时控制
- 输出捕获

参考项目：
- faif/python-patterns
"""

from typing import Any, Dict, List, Optional
import logging

from adapters.core.base_adapter import BaseAdapter
from adapters.core.types import AdapterConfig, AdapterResult, SkillContext

from .sandbox import SandboxValidator, SandboxConfig, create_sandbox_validator
from .executor import ShellExecutor, ExecutionConfig, ExecutionResult, create_executor


logger = logging.getLogger(__name__)


class ShellAdapter(BaseAdapter):
    """
    Shell 适配器

    支持执行命令行工具，提供沙箱安全机制。

    配置示例:
        config = AdapterConfig(
            type=AdapterType.SHELL,
            name="git-tools",
            metadata={
                "work_dir": "/project",
                "sandbox": True,
                "allowed_commands": ["git", "npm", "pip"],
                "timeout": 60
            }
        )
    """

    def __init__(self, config: AdapterConfig):
        super().__init__(config)
        self._executor: Optional[ShellExecutor] = None
        self._work_dir = config.metadata.get("work_dir", ".")
        self._sandbox_enabled = config.metadata.get("sandbox", True)

    async def initialize(self) -> bool:
        """初始化 Shell 适配器"""
        try:
            # 解析允许的命令
            allowed_commands = set(
                self.config.metadata.get("allowed_commands", [])
            )

            # 创建执行器
            self._executor = create_executor(
                work_dir=self._work_dir,
                allowed_commands=allowed_commands if allowed_commands else None,
                timeout=self.config.timeout,
            )

            logger.info(f"Shell 适配器初始化完成: {self.name}")
            return True

        except Exception as e:
            logger.error(f"Shell 适配器初始化失败: {e}")
            return False

    async def execute(
        self,
        context: SkillContext,
        input_data: Dict[str, Any]
    ) -> AdapterResult:
        """
        执行 Shell 命令

        Args:
            context: 技能执行上下文
            input_data: 输入数据，包含 command 字段

        Returns:
            AdapterResult: 执行结果
        """
        if not self._executor:
            return AdapterResult(
                success=False,
                data=None,
                error="Shell 执行器未初始化"
            )

        command = input_data.get("command", "")
        timeout = input_data.get("timeout", self.config.timeout)
        work_dir = input_data.get("work_dir")

        # 执行命令
        result = await self._executor.execute(
            command=command,
            timeout=timeout,
            work_dir=work_dir,
        )

        return AdapterResult(
            success=result.success,
            data=result.stdout if result.success else None,
            error=result.error or result.stderr if not result.success else None,
            metadata={
                "return_code": result.return_code,
                "elapsed": result.elapsed,
                "command": result.command,
                "timeout": result.timeout,
                "killed": result.killed,
            }
        )

    async def health_check(self) -> bool:
        """健康检查"""
        if not self._executor:
            return False
        return await self._executor.health_check()

    async def cleanup(self):
        """清理资源"""
        if self._executor:
            self._executor.kill_all()
            self._executor = None

    @property
    def allowed_commands(self) -> List[str]:
        """获取允许的命令列表"""
        if not self._executor:
            return []
        return self._executor.allowed_commands

    def add_allowed_command(self, command: str) -> None:
        """添加允许的命令"""
        if self._executor:
            self._executor.add_allowed_command(command)

    def remove_allowed_command(self, command: str) -> None:
        """移除允许的命令"""
        if self._executor:
            self._executor.remove_allowed_command(command)

    def validate_command(self, command: str) -> tuple:
        """
        验证命令（不执行）

        Args:
            command: 命令

        Returns:
            tuple: (是否安全, 错误信息)
        """
        if not self._executor:
            return False, "执行器未初始化"
        return self._executor.validate(command)

    async def execute_batch(
        self,
        commands: List[str],
        parallel: bool = False,
    ) -> List[AdapterResult]:
        """
        批量执行命令

        Args:
            commands: 命令列表
            parallel: 是否并行执行

        Returns:
            List[AdapterResult]: 结果列表
        """
        if not self._executor:
            return [
                AdapterResult(success=False, data=None, error="执行器未初始化")
                for _ in commands
            ]

        results = await self._executor.execute_batch(commands, parallel)

        return [
            AdapterResult(
                success=r.success,
                data=r.stdout if r.success else None,
                error=r.error or r.stderr if not r.success else None,
                metadata={
                    "return_code": r.return_code,
                    "elapsed": r.elapsed,
                    "command": r.command,
                }
            )
            for r in results
        ]
