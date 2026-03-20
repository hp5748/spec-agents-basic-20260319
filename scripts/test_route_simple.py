"""
简化的路由测试 - 只测试 Skill 路由
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.stream_agent import StreamAgent


async def test_skill_only():
    """只测试 Skill 路由（不需要 LLM）"""
    print("\n" + "=" * 50)
    print("Skill 路由测试")
    print("=" * 50)

    agent = StreamAgent(
        session_id="test_skill_only",
        project_root="."
    )

    # 只调用 _try_skill，不触发 LLM
    agent._init_skills()
    result = await agent._try_skill("查询所有用户")

    if result and result.success:
        print(f"\nSkill 响应: {result.response[:100]}...")

        # 检查调用链
        chain = agent._chain_tracker.format_signature()
        print(f"调用链: {chain}")

        if "[Skill:" in chain:
            print("\n[OK] Skill 调用链正确")
            return True
        else:
            print("\n[FAIL] Skill 调用链缺失")
            return False
    else:
        print("\n[INFO] Skill 未匹配（可能需要配置）")
        return False


async def test_chain_tracker():
    """测试 ChainTracker"""
    print("\n" + "=" * 50)
    print("ChainTracker 测试")
    print("=" * 50)

    from src.agent.chain_tracker import ChainTracker

    tracker = ChainTracker()

    # 测试 Skill 调用链
    tracker.add("skill", "sqlite-query-skill", 0.9)
    tracker.add("mcp", "filesystem", 0.8)

    signature = tracker.format_signature()
    print(f"\n调用链签名: {signature}")

    if "[Skill: sqlite-query-skill → MCP: filesystem]" in signature:
        print("\n[OK] ChainTracker 工作正常")
        return True
    else:
        print("\n[FAIL] ChainTracker 格式错误")
        return False


async def test_llm_signature():
    """测试 LLM 签名"""
    print("\n" + "=" * 50)
    print("LLM 签名测试")
    print("=" * 50)

    from src.agent.chain_tracker import ChainTracker

    tracker = ChainTracker()
    signature = tracker.format_signature()
    print(f"\n空链签名: '{signature}'")

    if "[LLM]" in signature:
        print("\n[OK] LLM 签名正确")
        return True
    else:
        print("\n[FAIL] LLM 签名错误")
        return False


async def main():
    print("\n" + "=" * 60)
    print("       简化路由测试")
    print("=" * 60)

    results = []

    results.append(await test_chain_tracker())
    results.append(await test_llm_signature())
    results.append(await test_skill_only())

    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"测试结果: {passed}/{total} 通过")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
