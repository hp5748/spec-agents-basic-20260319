#!/usr/bin/env python3
"""
调用链签名功能测试脚本

验证 StreamAgent 在响应结尾正确显示调用来源标识。
"""

import sys
import asyncio
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.stream_agent import StreamAgent


async def test_skill_call():
    """测试 Skill 调用签名"""
    print("=" * 60)
    print("测试1: Skill 调用签名")
    print("=" * 60)

    agent = StreamAgent("test-session-1")

    # 使用 sqlite-query-skill 的触发关键词
    response = await agent.chat("查询所有用户")

    print(f"\n响应:\n{response}")
    print()

    # 验证签名
    if "[Skill:" in response:
        print("[OK] Skill 签名显示正确")
        return True
    else:
        print("[FAIL] 缺少 Skill 签名")
        return False


async def test_llm_call():
    """测试 LLM 直接回答签名"""
    print("\n" + "=" * 60)
    print("测试2: LLM 直接回答签名")
    print("=" * 60)

    agent = StreamAgent("test-session-2")

    # 使用普通问候语，不应触发 Skill
    response = await agent.chat("你好")

    print(f"\n响应:\n{response}")
    print()

    # 验证签名
    if "[LLM]" in response:
        print("[OK] LLM 签名显示正确")
        return True
    else:
        print("[FAIL] 缺少 LLM 签名")
        return False


async def test_streaming_skill_call():
    """测试流式响应 Skill 调用签名"""
    print("\n" + "=" * 60)
    print("测试3: 流式响应 Skill 调用签名")
    print("=" * 60)

    agent = StreamAgent("test-session-3")

    response_chunks = []
    async for chunk in agent.chat_stream("查询张三的信息"):
        response_chunks.append(chunk)

    full_response = "".join(response_chunks)
    print(f"\n响应:\n{full_response}")
    print()

    # 验证签名
    if "[Skill:" in full_response:
        print("[OK] 流式响应 Skill 签名显示正确")
        return True
    else:
        print("[FAIL] 流式响应缺少 Skill 签名")
        return False


async def test_streaming_llm_call():
    """测试流式响应 LLM 直接回答签名"""
    print("\n" + "=" * 60)
    print("测试4: 流式响应 LLM 直接回答签名")
    print("=" * 60)

    agent = StreamAgent("test-session-4")

    response_chunks = []
    async for chunk in agent.chat_stream("今天天气怎么样"):
        response_chunks.append(chunk)

    full_response = "".join(response_chunks)
    print(f"\n响应:\n{full_response}")
    print()

    # 验证签名
    if "[LLM]" in full_response:
        print("[OK] 流式响应 LLM 签名显示正确")
        return True
    else:
        print("[FAIL] 流式响应缺少 LLM 签名")
        return False


async def main():
    """运行所有测试"""
    print("\n调用链签名功能测试")
    print("=" * 60)
    print()

    results = []

    # 运行测试
    results.append(await test_skill_call())
    results.append(await test_llm_call())
    results.append(await test_streaming_skill_call())
    results.append(await test_streaming_llm_call())

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    print(f"\n通过: {passed}/{total}")

    if passed == total:
        print("\n[OK] 所有测试通过!")
    else:
        print(f"\n[FAIL] {total - passed} 个测试失败")

    print("=" * 60)

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
