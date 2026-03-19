"""
Shell 执行器

增强的命令执行器，支持：
- 沙箱安全
- 资源限制
- 超时控制
- 输出捕获
- 并发控制

参考：
- subprocess 模块
- resource 模块 (Unix)
- Docker 容器执行
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import asyncio
import logging
import time
import os
import signal

from .sandbox import SandboxValidator, SandboxConfig, create_sandbox_validator


logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    stdout: str
    stderr: str
    return_code: int
    elapsed: float
    command: str
    error: Optional[str] = None
    timeout: bool = False
    killed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "return_code": self.return_code,
            "elapsed": self.elapsed,
            "command": self.command,
            "error": self.error,
            "timeout": self.timeout,
            "killed": self.killed,
        }


@dataclass
class ExecutionConfig:
    """执行配置"""
    timeout: float = 30.0
    max_output_size: int = 1024 * 1024  # 1MB
    work_dir: Optional[str] = None
    env: Dict[str, str] = field(default_factory=dict)
    shell: bool = True

    # 资源限制
    max_memory_mb: int = 512
    max_cpu_percent: int = 80

    # 并发控制
    max_concurrent: int = 5


class ShellExecutor:
    """
    Shell 执行器

    安全地执行 Shell 命令。

    使用方式：
        executor = ShellExecutor(work_dir="/project")

        # 执行命令
        result = executor.execute("git status")
        if result.success:
            print(result.stdout)
    """

    def __init__(
        self,
        work_dir: Optional[str] = None,
        sandbox: Optional[SandboxValidator] = None,
        config: Optional[ExecutionConfig] = None,
    ):
        """
        初始化执行器

        Args:
            work_dir: 工作目录
            sandbox: 沙箱验证器
            config: 执行配置
        """
        self.work_dir = Path(work_dir) if work_dir else Path.cwd()
        self.sandbox = sandbox or create_sandbox_validator(work_dir=str(self.work_dir))
        self.config = config or ExecutionConfig()

        # 并发控制
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent)
        self._running_processes: Dict[int, asyncio.subprocess.Process] = {}

    @property
    def allowed_commands(self) -> List[str]:
        """获取允许的命令列表"""
        return list(self.sandbox.config.allowed_commands)

    def add_allowed_command(self, command: str) -> None:
        """添加允许的命令"""
        self.sandbox.config.allowed_commands.add(command)

    def remove_allowed_command(self, command: str) -> None:
        """移除允许的命令"""
        self.sandbox.config.allowed_commands.discard(command)

    def validate(self, command: str) -> Tuple[bool, Optional[str]]:
        """验证命令"""
        return self.sandbox.validate_command(command)

    async def execute(
        self,
        command: str,
        timeout: Optional[float] = None,
        work_dir: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> ExecutionResult:
        """
        执行命令

        Args:
            command: 命令
            timeout: 超时时间（秒）
            work_dir: 工作目录
            env: 环境变量

        Returns:
            ExecutionResult: 执行结果
        """
        # 验证命令
        is_valid, error = self.sandbox.validate_command(command)
        if not is_valid:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="",
                return_code=-1,
                elapsed=0,
                command=command,
                error=error,
            )

        # 使用并发控制
        async with self._semaphore:
            return await self._execute_internal(
                command,
                timeout=timeout,
                work_dir=work_dir,
                env=env,
            )

    async def _execute_internal(
        self,
        command: str,
        timeout: Optional[float] = None,
        work_dir: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> ExecutionResult:
        """内部执行逻辑"""
        start_time = time.time()
        timeout = timeout or self.config.timeout
        cwd = Path(work_dir) if work_dir else self.work_dir

        # 验证工作目录
        if not cwd.exists():
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="",
                return_code=-1,
                elapsed=0,
                command=command,
                error=f"工作目录不存在: {cwd}",
            )

        # 构建环境变量
        process_env = dict(os.environ)
        if env:
            # 过滤环境变量
            filtered_env = self.sandbox.filter_env(env)
            process_env.update(filtered_env)

        try:
            # 创建进程
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(cwd),
                env=process_env,
                preexec_fn=self._set_resource_limits if os.name != "nt" else None,
            )

            # 记录运行中的进程
            self._running_processes[process.pid] = process

            try:
                # 等待完成（带超时）
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                # 超时，终止进程
                process.kill()
                await process.wait()

                return ExecutionResult(
                    success=False,
                    stdout="",
                    stderr="",
                    return_code=-1,
                    elapsed=time.time() - start_time,
                    command=command,
                    error=f"命令执行超时 ({timeout}s)",
                    timeout=True,
                    killed=True,
                )
            finally:
                # 清理记录
                self._running_processes.pop(process.pid, None)

            # 解码输出
            stdout_str = self._decode_output(stdout)
            stderr_str = self._decode_output(stderr)

            # 截断输出
            if len(stdout_str) > self.config.max_output_size:
                stdout_str = stdout_str[:self.config.max_output_size] + "\n... (输出已截断)"
            if len(stderr_str) > self.config.max_output_size:
                stderr_str = stderr_str[:self.config.max_output_size] + "\n... (错误输出已截断)"

            return ExecutionResult(
                success=process.returncode == 0,
                stdout=stdout_str,
                stderr=stderr_str,
                return_code=process.returncode,
                elapsed=time.time() - start_time,
                command=command,
                error=stderr_str if process.returncode != 0 else None,
            )

        except Exception as e:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="",
                return_code=-1,
                elapsed=time.time() - start_time,
                command=command,
                error=f"执行异常: {str(e)}",
            )

    def _decode_output(self, data: bytes) -> str:
        """解码输出"""
        if not data:
            return ""

        # 尝试多种编码
        encodings = ["utf-8", "gbk", "gb2312", "latin-1"]
        for encoding in encodings:
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue

        # 最终回退
        return data.decode("utf-8", errors="replace")

    def _set_resource_limits(self):
        """设置资源限制（仅 Unix）"""
        try:
            import resource

            # 内存限制
            memory_bytes = self.config.max_memory_mb * 1024 * 1024
            resource.setrlimit(
                resource.RLIMIT_AS,
                (memory_bytes, memory_bytes)
            )

            # CPU 时间限制
            resource.setrlimit(
                resource.RLIMIT_CPU,
                (self.config.timeout, self.config.timeout + 1)
            )

        except Exception as e:
            logger.warning(f"设置资源限制失败: {e}")

    async def execute_batch(
        self,
        commands: List[str],
        parallel: bool = False,
    ) -> List[ExecutionResult]:
        """
        批量执行命令

        Args:
            commands: 命令列表
            parallel: 是否并行执行

        Returns:
            List[ExecutionResult]: 结果列表
        """
        if parallel:
            tasks = [self.execute(cmd) for cmd in commands]
            return await asyncio.gather(*tasks)
        else:
            results = []
            for cmd in commands:
                result = await self.execute(cmd)
                results.append(result)
            return results

    def kill_all(self) -> None:
        """终止所有运行中的进程"""
        for pid, process in list(self._running_processes.items()):
            try:
                process.kill()
                logger.info(f"已终止进程: {pid}")
            except Exception as e:
                logger.error(f"终止进程失败 {pid}: {e}")

        self._running_processes.clear()

    async def health_check(self) -> bool:
        """健康检查"""
        return self.work_dir.exists()


def create_executor(
    work_dir: Optional[str] = None,
    allowed_commands: Optional[set] = None,
    **kwargs
) -> ShellExecutor:
    """
    工厂函数：创建执行器

    Args:
        work_dir: 工作目录
        allowed_commands: 允许的命令
        **kwargs: 其他配置

    Returns:
        ShellExecutor: 执行器实例
    """
    sandbox = create_sandbox_validator(
        allowed_commands=allowed_commands,
        work_dir=work_dir,
    )

    config = ExecutionConfig(
        work_dir=work_dir,
        **kwargs
    )

    return ShellExecutor(
        work_dir=work_dir,
        sandbox=sandbox,
        config=config,
    )
