#!/usr/bin/env python3
"""快速测试调用链签名"""
import sys
sys.path.insert(0, ".")

import asyncio
from src.agent.stream_agent import StreamAgent


async def main():
    print("=" * 60)
    print("调用链签名验证测试")
    print("=" * 60)
    print()

    # 测试1: Skill 调用
    print("【测试1】Skill 调用签名")
    print("-" * 40)
    agent1 = StreamAgent("test-1")
    response1 = await agent1.chat("查询所有用户")
    print(response1)
    print()

    # 测试2: LLM 直接回答（如果 API 可用）
    print("【测试2】LLM 直接回答签名")
    print("-" * 40)
    try:
        agent2 = StreamAgent("test-2")
        response2 = await agent2.chat("你好")
        print(response2)
    except Exception as e:
        print(f"LLM API 调用失败（预期）: {e}")
    print()

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
