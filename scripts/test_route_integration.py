"""
路由集成测试脚本

测试 Skill/SubAgent/MCP/LLM 的调用链显示。
"""

import asyncio
import sys
import os

# Windows 控制台编码设置
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.stream_agent import StreamAgent


async def test_skill_routing():
    """测试 Skill 路由"""
    print("\n" + "=" * 50)
    print("测试 1: Skill 路由（查询用户）")
    print("=" * 50)

    agent = StreamAgent(
        session_id="test_skill",
        project_root="."
    )

    response = await agent.chat("查询所有用户", include_history=False)

    print(f"\n响应:\n{response}")

    if "[Skill:" in response:
        print("\n[OK] Skill 调用链显示正确")
    else:
        print("\n[FAIL] Skill 调用链未显示")


async def test_subagent_routing():
    """测试 SubAgent 路由"""
    print("\n" + "=" * 50)
    print("测试 2: SubAgent 路由（代码分析）")
    print("=" * 50)

    agent = StreamAgent(
        session_id="test_subagent",
        project_root="."
    )

    response = await agent.chat("分析这段代码的缺陷", include_history=False)

    print(f"\n响应:\n{response}")

    if "[SubAgent:" in response:
        print("\n[OK] SubAgent 调用链显示正确")
    else:
        print("\n[FAIL] SubAgent 调用链未显示（可能未配置 SubAgent）")


async def test_mcp_routing():
    """测试 MCP 路由"""
    print("\n" + "=" * 50)
    print("测试 3: MCP 路由（文件操作）")
    print("=" * 50)

    agent = StreamAgent(
        session_id="test_mcp",
        project_root="."
    )

    response = await agent.chat("读取 README.md 文件", include_history=False)

    print(f"\n响应:\n{response}")

    if "[MCP:" in response:
        print("\n[OK] MCP 调用链显示正确")
    else:
        print("\n[FAIL] MCP 调用链未显示（可能未配置 MCP）")


async def test_llm_fallback():
    """测试 LLM 降级"""
    print("\n" + "=" * 50)
    print("测试 4: LLM 降级（普通对话）")
    print("=" * 50)

    agent = StreamAgent(
        session_id="test_llm",
        project_root="."
    )

    response = await agent.chat("你好，今天天气怎么样？", include_history=False)

    print(f"\n响应:\n{response}")

    if "[LLM]" in response:
        print("\n[OK] LLM 调用链显示正确")
    else:
        print("\n[FAIL] LLM 调用链未显示")


async def test_stream_routing():
    """测试流式路由"""
    print("\n" + "=" * 50)
    print("测试 5: 流式路由")
    print("=" * 50)

    agent = StreamAgent(
        session_id="test_stream",
        project_root="."
    )

    print("\n流式响应:")
    full_response = ""
    async for chunk in agent.chat_stream("查询用户信息", include_history=False):
        print(chunk, end="", flush=True)
        full_response += chunk

    print("\n")

    if "[Skill:" in full_response or "[LLM]" in full_response:
        print("[OK] 流式调用链显示正确")
    else:
        print("[FAIL] 流式调用链未显示")


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("       路由集成测试 - Skill/SubAgent/MCP/LLM")
    print("=" * 60)

    try:
        # 运行测试
        await test_skill_routing()
        await test_subagent_routing()
        await test_mcp_routing()
        await test_llm_fallback()
        await test_stream_routing()

        print("\n" + "=" * 60)
        print("测试完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
