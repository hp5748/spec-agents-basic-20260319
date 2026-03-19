"""
Shell 沙箱环境

提供安全的命令执行环境，包括：
- 命令白名单/黑名单
- 危险命令检测
- 资源限制（CPU、内存、时间）
- 文件系统隔离
- 环境变量过滤

参考：
- Docker 容器安全
- Linux namespaces
- seccomp
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from pathlib import Path
import re
import logging


logger = logging.getLogger(__name__)


@dataclass
class SandboxConfig:
    """沙箱配置"""
    enabled: bool = True

    # 命令控制
    whitelist_enabled: bool = True
    blacklist_enabled: bool = True
    allowed_commands: Set[str] = field(default_factory=set)
    blocked_commands: Set[str] = field(default_factory=set)

    # 路径控制
    allowed_paths: Set[str] = field(default_factory=set)
    blocked_paths: Set[str] = field(default_factory=set)
    allow_write: bool = False
    allow_network: bool = False

    # 资源限制
    max_cpu_time: int = 30  # 秒
    max_memory_mb: int = 512  # MB
    max_output_size: int = 1024 * 1024  # 1MB
    max_file_size: int = 10 * 1024 * 1024  # 10MB

    # 环境变量
    allowed_env_vars: Set[str] = field(default_factory=set)
    blocked_env_patterns: List[str] = field(default_factory=list)


# 默认允许的命令（安全命令）
DEFAULT_ALLOWED_COMMANDS: Set[str] = {
    # 版本控制
    "git", "svn", "hg",
    # 包管理
    "npm", "yarn", "pnpm", "pip", "pip3", "poetry", "cargo",
    # 语言运行时
    "python", "python3", "node", "deno", "bun", "go", "rustc",
    # 构建工具
    "make", "cmake", "gradle", "mvn",
    # 容器
    "docker", "docker-compose",
    # Kubernetes
    "kubectl", "helm", "kustomize",
    # 基础设施
    "terraform", "ansible", "vagrant",
    # 文件操作（只读）
    "ls", "cat", "head", "tail", "grep", "find", "wc", "sort", "uniq",
    "diff", "tree", "file",
    # 文本处理
    "sed", "awk", "cut", "tr", "echo",
    # 网络（受限）
    "curl", "wget",
}

# 默认禁止的命令（危险命令）
DEFAULT_BLOCKED_COMMANDS: Set[str] = {
    # 系统破坏
    "rm", "rmdir", "del", "format", "mkfs",
    # 权限提升
    "sudo", "su", "doas", "pkexec", "chmod", "chown",
    # 用户管理
    "useradd", "userdel", "usermod", "passwd",
    # 网络危险操作
    "iptables", "ufw", "firewall-cmd", "nc", "netcat",
    # 进程管理
    "kill", "killall", "pkill", "xargs",
    # 系统控制
    "shutdown", "reboot", "halt", "poweroff", "init",
    # 内核操作
    "modprobe", "insmod", "rmmod", "sysctl",
    # 磁盘操作
    "dd", "fdisk", "parted", "mount", "umount",
    # 危险脚本
    "eval", "exec",
}

# 危险命令模式（正则表达式）
DANGEROUS_PATTERNS: List[str] = [
    # 系统破坏
    r"rm\s+-rf\s+/",
    r"rm\s+-rf\s+~",
    r"rm\s+-rf\s+\*",
    r"mkfs",
    r"dd\s+if=",
    r">\s*/dev/sd[a-z]",
    r">\s*/dev/hd[a-z]",

    # 权限绕过
    r"chmod\s+777",
    r"chown\s+root",
    r"sudo\s+chmod",
    r"sudo\s+chown",

    # 网络危险
    r">\s*/dev/tcp/",
    r">\s*/dev/udp/",
    r"nc\s+-l",
    r"netcat\s+-l",

    # Shell 注入
    r";\s*rm",
    r"\|\s*rm",
    r"`.*rm.*`",
    r"\$\{.*rm.*\}",
    r"\$\([^)]*rm[^)]*\)",

    # 敏感文件
    r"/etc/shadow",
    r"/etc/passwd",
    r"/root/\.ssh",
    r"~/.ssh",
    r"\.pem",
    r"\.key",
    r"id_rsa",

    # Fork 炸弹
    r":\(\)\s*\{\s*:\|:&\s*\}\s*;:",

    # 环境变量注入
    r"LD_PRELOAD",
    r"LD_LIBRARY_PATH",
]


class SandboxValidator:
    """
    沙箱验证器

    验证命令是否安全可执行。

    使用方式：
        validator = SandboxValidator(config)
        is_safe, error = validator.validate_command("git status")
        if is_safe:
            # 执行命令
            pass
    """

    def __init__(self, config: Optional[SandboxConfig] = None):
        """
        初始化验证器

        Args:
            config: 沙箱配置
        """
        self.config = config or SandboxConfig(
            allowed_commands=DEFAULT_ALLOWED_COMMANDS.copy(),
            blocked_commands=DEFAULT_BLOCKED_COMMANDS.copy(),
        )

        # 编译危险模式正则
        self._dangerous_patterns = [
            re.compile(p, re.IGNORECASE) for p in DANGEROUS_PATTERNS
        ]

    def validate_command(self, command: str) -> Tuple[bool, Optional[str]]:
        """
        验证命令是否安全

        Args:
            command: 待验证的命令

        Returns:
            Tuple[bool, Optional[str]]: (是否安全, 错误信息)
        """
        if not command or not command.strip():
            return False, "命令不能为空"

        command = command.strip()

        # 1. 检查黑名单
        if self.config.blacklist_enabled:
            cmd_base = self._extract_base_command(command)
            if cmd_base in self.config.blocked_commands:
                return False, f"命令在黑名单中: {cmd_base}"

        # 2. 检查白名单
        if self.config.whitelist_enabled:
            cmd_base = self._extract_base_command(command)
            if cmd_base not in self.config.allowed_commands:
                return False, f"命令不在白名单中: {cmd_base}"

        # 3. 检查危险模式
        for pattern in self._dangerous_patterns:
            if pattern.search(command):
                return False, f"检测到危险命令模式: {pattern.pattern}"

        # 4. 检查路径访问
        path_error = self._validate_paths(command)
        if path_error:
            return False, path_error

        # 5. 检查环境变量
        env_error = self._validate_env_vars(command)
        if env_error:
            return False, env_error

        return True, None

    def _extract_base_command(self, command: str) -> str:
        """提取命令基础名称"""
        # 去除前导空格和 sudo
        cmd = command.strip()
        if cmd.startswith("sudo "):
            cmd = cmd[5:].strip()

        # 获取第一个词
        parts = cmd.split()
        if not parts:
            return ""

        # 提取命令名（去除路径）
        cmd_path = parts[0]
        return cmd_path.split("/")[-1] if "/" in cmd_path else cmd_path

    def _validate_paths(self, command: str) -> Optional[str]:
        """验证路径访问"""
        # 检查阻止的路径
        for blocked in self.config.blocked_paths:
            if blocked in command:
                return f"访问被阻止的路径: {blocked}"

        # 检查写入操作
        if not self.config.allow_write:
            write_patterns = [
                r">\s*",  # 重定向写入
                r">>\s*",  # 追加写入
                r"touch\s+",
                r"mkdir\s+",
                r"cp\s+.*\s+",
                r"mv\s+.*\s+",
            ]
            for pattern in write_patterns:
                if re.search(pattern, command):
                    # 检查是否在允许的路径内
                    # 简化处理：禁止所有写入
                    return "沙箱模式下禁止写入操作"

        return None

    def _validate_env_vars(self, command: str) -> Optional[str]:
        """验证环境变量"""
        # 检查危险环境变量
        for pattern in self.config.blocked_env_patterns:
            if pattern in command:
                return f"检测到危险环境变量模式: {pattern}"

        # 检查 LD_PRELOAD 等
        dangerous_vars = ["LD_PRELOAD", "LD_LIBRARY_PATH", "DYLD_INSERT_LIBRARIES"]
        for var in dangerous_vars:
            if var in command:
                return f"禁止设置环境变量: {var}"

        return None

    def validate_path(self, path: str) -> Tuple[bool, Optional[str]]:
        """
        验证路径是否可访问

        Args:
            path: 路径

        Returns:
            Tuple[bool, Optional[str]]: (是否可访问, 错误信息)
        """
        abs_path = str(Path(path).resolve())

        # 检查阻止的路径
        for blocked in self.config.blocked_paths:
            if abs_path.startswith(blocked):
                return False, f"路径被阻止: {path}"

        # 如果设置了允许的路径，则必须在其中
        if self.config.allowed_paths:
            in_allowed = False
            for allowed in self.config.allowed_paths:
                if abs_path.startswith(allowed):
                    in_allowed = True
                    break
            if not in_allowed:
                return False, f"路径不在允许范围内: {path}"

        return True, None

    def filter_env(self, env: Dict[str, str]) -> Dict[str, str]:
        """
        过滤环境变量

        Args:
            env: 原始环境变量

        Returns:
            Dict[str, str]: 过滤后的环境变量
        """
        filtered = {}

        for key, value in env.items():
            # 检查是否在阻止列表
            if key in self.config.blocked_env_patterns:
                continue

            # 检查是否在允许列表（如果设置了）
            if self.config.allowed_env_vars:
                if key not in self.config.allowed_env_vars:
                    continue

            # 检查危险变量
            if key in ["LD_PRELOAD", "LD_LIBRARY_PATH", "DYLD_INSERT_LIBRARIES"]:
                continue

            filtered[key] = value

        return filtered


def create_sandbox_validator(
    allowed_commands: Optional[Set[str]] = None,
    blocked_commands: Optional[Set[str]] = None,
    work_dir: Optional[str] = None,
    **kwargs
) -> SandboxValidator:
    """
    工厂函数：创建沙箱验证器

    Args:
        allowed_commands: 允许的命令
        blocked_commands: 禁止的命令
        work_dir: 工作目录（自动添加到允许路径）
        **kwargs: 其他配置

    Returns:
        SandboxValidator: 验证器实例
    """
    config = SandboxConfig(
        allowed_commands=allowed_commands or DEFAULT_ALLOWED_COMMANDS.copy(),
        blocked_commands=blocked_commands or DEFAULT_BLOCKED_COMMANDS.copy(),
        **kwargs
    )

    # 添加工作目录到允许路径
    if work_dir:
        config.allowed_paths.add(str(Path(work_dir).resolve()))

    return SandboxValidator(config)
