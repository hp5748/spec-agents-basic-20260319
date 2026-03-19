"""
适配器基类

所有适配器必须继承此基类并实现抽象方法。

参考：
- Python 设计模式 (faif/python-patterns)
- MCP 协议规范 (modelcontextprotocol)
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, Optional
import logging
import time

from .types import AdapterConfig, AdapterResult, SkillContext, ExecutionTrace, ExecutionStatus


logger = logging.getLogger(__name__)


class BaseAdapter(ABC):
    """
    适配器基类

    所有适配器必须继承此类并实现以下抽象方法：
    - execute(): 执行适配器逻辑
    - health_check(): 健康检查

    可选覆盖：
    - initialize(): 初始化适配器
    - cleanup(): 清理资源
    - execute_stream(): 流式执行
    """

    def __init__(self, config: AdapterConfig):
        """
        初始化适配器

        Args:
            config: 适配器配置
        """
        self.config = config
        self._initialized = False
        self._last_health_check: Optional[bool] = None
        self._execution_count = 0

    @property
    def name(self) -> str:
        """适配器名称"""
        return self.config.name

    @property
    def adapter_type(self) -> str:
        """适配器类型"""
        return self.config.type.value

    @abstractmethod
    async def execute(
        self,
        context: SkillContext,
        input_data: Dict[str, Any]
    ) -> AdapterResult:
        """
        执行适配器

        Args:
            context: 技能执行上下文
            input_data: 输入数据

        Returns:
            AdapterResult: 执行结果
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        健康检查

        Returns:
            bool: 健康状态
        """
        pass

    async def initialize(self) -> bool:
        """
        初始化适配器

        子类可覆盖此方法执行初始化逻辑，如：
        - 建立连接
        - 加载配置
        - 预热缓存

        Returns:
            bool: 初始化是否成功
        """
        logger.info(f"初始化适配器: {self.name}")
        self._initialized = True
        return True

    async def cleanup(self):
        """
        清理资源

        子类可覆盖此方法执行清理逻辑，如：
        - 关闭连接
        - 释放资源
        - 保存状态
        """
        logger.info(f"清理适配器: {self.name}")
        self._initialized = False

    async def execute_stream(
        self,
        context: SkillContext,
        input_data: Dict[str, Any]
    ) -> AsyncIterator[str]:
        """
        流式执行（可选实现）

        默认实现将 execute 结果转为流式输出。
        子类可覆盖此方法实现真正的流式处理。

        Args:
            context: 技能执行上下文
            input_data: 输入数据

        Yields:
            str: 流式输出内容
        """
        result = await self.execute(context, input_data)
        if result.success:
            yield str(result.data)
        else:
            yield f"Error: {result.error}"

    async def execute_with_trace(
        self,
        context: SkillContext,
        input_data: Dict[str, Any]
    ) -> tuple[AdapterResult, ExecutionTrace]:
        """
        带追踪的执行

        自动记录执行时间、状态等信息。

        Args:
            context: 技能执行上下文
            input_data: 输入数据

        Returns:
            tuple: (执行结果, 执行追踪)
        """
        trace_id = f"{self.name}_{context.session_id}_{time.time_ns()}"
        trace = ExecutionTrace(
            trace_id=trace_id,
            adapter_name=self.name,
            status=ExecutionStatus.RUNNING,
            start_time=time.time(),
        )

        try:
            self._execution_count += 1
            result = await self.execute(context, input_data)

            trace.end_time = time.time()
            trace.status = ExecutionStatus.SUCCESS if result.success else ExecutionStatus.FAILED
            trace.result = result

            logger.info(
                f"适配器执行完成: {self.name}, "
                f"状态: {trace.status.value}, "
                f"耗时: {trace.elapsed_time:.3f}s"
            )

            return result, trace

        except Exception as e:
            trace.end_time = time.time()
            trace.status = ExecutionStatus.FAILED
            trace.result = AdapterResult(
                success=False,
                data=None,
                error=str(e),
                metadata={"exception": type(e).__name__}
            )

            logger.error(f"适配器执行异常: {self.name}, 错误: {e}")

            return trace.result, trace

    def validate_input(
        self,
        input_data: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> bool:
        """
        验证输入数据

        使用 JSON Schema 验证输入数据格式。

        Args:
            input_data: 输入数据
            schema: JSON Schema 定义

        Returns:
            bool: 验证是否通过
        """
        try:
            import jsonschema
            jsonschema.validate(instance=input_data, schema=schema)
            return True
        except ImportError:
            logger.warning("jsonschema 未安装，跳过验证")
            return True
        except jsonschema.ValidationError as e:
            logger.warning(f"输入验证失败: {e.message}")
            return False

    def validate_output(
        self,
        output_data: Any,
        schema: Dict[str, Any]
    ) -> bool:
        """
        验证输出数据

        Args:
            output_data: 输出数据
            schema: JSON Schema 定义

        Returns:
            bool: 验证是否通过
        """
        try:
            import jsonschema
            jsonschema.validate(instance=output_data, schema=schema)
            return True
        except ImportError:
            return True
        except jsonschema.ValidationError:
            return False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, type={self.adapter_type})"


class PythonAdapter(BaseAdapter):
    """
    Python 执行器适配器

    执行 Skill 内置的 Python 脚本。
    这是默认适配器，保持与现有 Skill 的兼容性。
    """

    async def execute(
        self,
        context: SkillContext,
        input_data: Dict[str, Any]
    ) -> AdapterResult:
        """
        执行 Python 脚本

        动态加载 executor.py 并执行。
        """
        import importlib.util
        from pathlib import Path

        entry = self.config.metadata.get("entry", "scripts/executor.py")
        skill_path = self.config.metadata.get("skill_path", ".")

        executor_path = Path(skill_path) / entry

        if not executor_path.exists():
            return AdapterResult(
                success=False,
                data=None,
                error=f"执行器文件不存在: {executor_path}"
            )

        try:
            # 动态加载模块
            spec = importlib.util.spec_from_file_location("executor", executor_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 获取执行器类
            executor_class = getattr(module, "SkillExecutor", None)
            if not executor_class:
                return AdapterResult(
                    success=False,
                    data=None,
                    error="执行器文件中未找到 SkillExecutor 类"
                )

            # 实例化并执行
            executor = executor_class()
            result = await executor.execute(context) if hasattr(executor, 'execute') else executor.execute(context)

            return AdapterResult(
                success=result.success if hasattr(result, 'success') else True,
                data=result.response if hasattr(result, 'response') else str(result),
                metadata={"used_tools": result.used_tools if hasattr(result, 'used_tools') else []}
            )

        except Exception as e:
            return AdapterResult(
                success=False,
                data=None,
                error=f"执行器执行失败: {str(e)}"
            )

    async def health_check(self) -> bool:
        """Python 执行器始终健康"""
        return True
