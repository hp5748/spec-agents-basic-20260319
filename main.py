"""
Super Agent to Skill - 主入口

一个基于 Skill 的 AI Agent 运行时。

使用方式:
    python main.py              # 交互模式
    python main.py --test       # 测试连接
    python main.py --skill http-example-skill --input "列出文章"
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from src.llm_client import LLMClient, LLMConfig
from src.adapter_manager import AdapterManager
from src.skill_loader import SkillLoader


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


class SuperAgent:
    """
    Super Agent

    基于 Skill 的 AI Agent，支持：
    - 多种适配器 (Python, HTTP, MCP, Shell)
    - 大模型对话
    - Skill 自动发现和执行
    """

    def __init__(self):
        self.llm_client: Optional[LLMClient] = None
        self.adapter_manager: Optional[AdapterManager] = None
        self.skill_loader: Optional[SkillLoader] = None
        self._initialized = False

    async def initialize(self) -> bool:
        """初始化 Agent"""
        if self._initialized:
            return True

        try:
            # 加载环境变量
            load_dotenv()

            # 初始化 LLM 客户端
            llm_config = LLMConfig.from_env("SILICONFLOW")
            if not llm_config.api_key:
                logger.warning("未配置 API Key，LLM 功能将不可用")
            else:
                self.llm_client = LLMClient(llm_config)
                logger.info(f"LLM 客户端初始化完成: {llm_config.model}")

            # 初始化适配器管理器
            config_path = Path("config/adapters.yaml")
            self.adapter_manager = AdapterManager(
                config_path if config_path.exists() else None
            )
            await self.adapter_manager.initialize()
            logger.info(f"适配器管理器初始化完成: {self.adapter_manager.list_available_types()}")

            # 初始化 Skill 加载器
            self.skill_loader = SkillLoader("skills")
            skills = self.skill_loader.list_skills()
            logger.info(f"已加载 {len(skills)} 个 Skill: {skills}")

            self._initialized = True
            return True

        except Exception as e:
            logger.error(f"Agent 初始化失败: {e}")
            return False

    async def chat(self, user_input: str) -> str:
        """
        与 Agent 对话

        Args:
            user_input: 用户输入

        Returns:
            str: Agent 回复
        """
        if not self.llm_client:
            return "错误：LLM 客户端未初始化，请检查 .env 配置"

        messages = [
            {
                "role": "system",
                "content": """你是一个智能助手，可以帮助用户完成各种任务。

当前可用的 Skill：
- http-example-skill: HTTP 适配器示例，可以调用 REST API
- mcp-example-skill: MCP 适配器示例，可以连接 MCP Server
- shell-example-skill: Shell 适配器示例，可以执行命令行工具

请根据用户需求选择合适的 Skill 来完成任务。"""
            },
            {"role": "user", "content": user_input}
        ]

        response = await self.llm_client.chat(messages)
        return response

    async def execute_skill(
        self,
        skill_name: str,
        input_data: dict
    ) -> dict:
        """
        执行 Skill

        Args:
            skill_name: Skill 名称
            input_data: 输入数据

        Returns:
            dict: 执行结果
        """
        if not self.skill_loader:
            return {"success": False, "error": "Skill 加载器未初始化"}

        # 加载 Skill 配置
        skill_config = self.skill_loader.load_skill(skill_name)
        if not skill_config:
            return {"success": False, "error": f"Skill 不存在: {skill_name}"}

        adapter_config = skill_config.get("adapter", {})
        adapter_type = adapter_config.get("type", "python")

        # Python 类型执行内置脚本
        if adapter_type == "python":
            return await self._execute_python_skill(skill_name, skill_config, input_data)

        # 其他类型使用适配器
        adapter = self.adapter_manager.get_adapter_for_skill(skill_config)
        if not adapter:
            return {"success": False, "error": f"无法获取适配器: {adapter_type}"}

        # 执行
        from adapters import SkillContext
        context = SkillContext(
            session_id="default",
            user_input=str(input_data),
            intent=skill_name
        )

        result = await adapter.execute(context, input_data)
        return result.to_dict()

    async def _execute_python_skill(
        self,
        skill_name: str,
        skill_config: dict,
        input_data: dict
    ) -> dict:
        """执行 Python Skill"""
        try:
            # 加载执行器
            skill_path = Path("skills") / skill_name / "scripts" / "executor.py"
            if not skill_path.exists():
                return {"success": False, "error": f"执行器不存在: {skill_path}"}

            # 动态导入
            import importlib.util
            spec = importlib.util.spec_from_file_location("executor", skill_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 创建上下文并执行
            from adapters import SkillContext
            context = SkillContext(
                session_id="default",
                user_input=str(input_data),
                intent=skill_name
            )

            executor = module.SkillExecutor()
            result = await executor.execute(context)
            return result.__dict__

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def test_connection(self) -> bool:
        """测试 API 连接"""
        if not self.llm_client:
            print("[X] LLM 客户端未初始化")
            return False

        print("[*] 测试 API 连接...")
        success = await self.llm_client.test_connection()
        if success:
            print("[OK] API 连接成功")
        else:
            print("[X] API 连接失败")
        return success

    async def run_interactive(self):
        """交互模式"""
        print("\n" + "=" * 50)
        print("  Super Agent to Skill - 交互模式")
        print("  输入 'exit' 或 'quit' 退出")
        print("  输入 'skills' 查看可用 Skill")
        print("  输入 'adapters' 查看可用适配器")
        print("=" * 50 + "\n")

        while True:
            try:
                user_input = input("[You]: ").strip()
                if not user_input:
                    continue

                if user_input.lower() in ["exit", "quit", "q"]:
                    print("[*] 再见!")
                    break

                if user_input.lower() == "skills":
                    skills = self.skill_loader.list_skills()
                    print(f"\n[Skills] 可用 Skill ({len(skills)}):")
                    for skill in skills:
                        info = self.skill_loader.load_skill(skill)
                        desc = info.get("description", "无描述") if info else "无描述"
                        print(f"  - {skill}: {desc}")
                    print()
                    continue

                if user_input.lower() == "adapters":
                    adapters = self.adapter_manager.list_available_types()
                    print(f"\n[Adapters] 可用适配器: {adapters}")
                    instances = self.adapter_manager.list_adapters()
                    print(f"[Instances] 已实例化: {instances}\n")
                    continue

                print("[Agent]: ", end="", flush=True)
                response = await self.chat(user_input)
                print(response + "\n")

            except KeyboardInterrupt:
                print("\n[*] 再见!")
                break
            except Exception as e:
                print(f"[Error] {e}\n")


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Super Agent to Skill")
    parser.add_argument("--test", action="store_true", help="测试 API 连接")
    parser.add_argument("--skill", type=str, help="执行指定 Skill")
    parser.add_argument("--input", type=str, help="Skill 输入 (JSON 格式)")

    args = parser.parse_args()

    # 创建 Agent
    agent = SuperAgent()
    initialized = await agent.initialize()

    if not initialized:
        print("[X] Agent 初始化失败")
        sys.exit(1)

    # 测试连接
    if args.test:
        await agent.test_connection()
        return

    # 执行 Skill
    if args.skill:
        import json
        input_data = json.loads(args.input) if args.input else {}
        result = await agent.execute_skill(args.skill, input_data)
        print(f"结果: {result}")
        return

    # 交互模式
    await agent.run_interactive()


if __name__ == "__main__":
    asyncio.run(main())
