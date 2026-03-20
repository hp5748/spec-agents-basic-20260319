#!/usr/bin/env python3
"""
ChainTracker 单元测试

直接测试 ChainTracker 类，不依赖 LLM API。
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.chain_tracker import ChainTracker, ChainInfo


def test_empty_chain():
    """测试空调用链（LLM 响应）"""
    print("测试1: 空调用链 (LLM 响应)")
    print("-" * 40)

    tracker = ChainTracker()
    signature = tracker.format_signature()

    print(f"签名: {repr(signature)}")

    expected = "\n\n[LLM]"
    if signature == expected:
        print(f"[OK] 空调用链返回 LLM 标识")
        return True
    else:
        print(f"[FAIL] 期望: {repr(expected)}, 实际: {repr(signature)}")
        return False


def test_skill_chain():
    """测试 Skill 调用链"""
    print("\n测试2: Skill 调用链")
    print("-" * 40)

    tracker = ChainTracker()
    tracker.add("skill", "sqlite-query-skill", 0.95)
    signature = tracker.format_signature()

    print(f"签名: {repr(signature)}")

    expected = "\n\n[Skill: sqlite-query-skill]"
    if signature == expected:
        print(f"[OK] Skill 调用链格式正确")
        return True
    else:
        print(f"[FAIL] 期望: {repr(expected)}, 实际: {repr(signature)}")
        return False


def test_subagent_chain():
    """测试 SubAgent 调用链"""
    print("\n测试3: SubAgent 调用链")
    print("-" * 40)

    tracker = ChainTracker()
    tracker.add("subagent", "code-analyzer", 0.88)
    signature = tracker.format_signature()

    print(f"签名: {repr(signature)}")

    expected = "\n\n[SubAgent: code-analyzer]"
    if signature == expected:
        print(f"[OK] SubAgent 调用链格式正确")
        return True
    else:
        print(f"[FAIL] 期望: {repr(expected)}, 实际: {repr(signature)}")
        return False


def test_mcp_chain():
    """测试 MCP 调用链"""
    print("\n测试4: MCP 调用链")
    print("-" * 40)

    tracker = ChainTracker()
    tracker.add("mcp", "filesystem", 1.0)
    signature = tracker.format_signature()

    print(f"签名: {repr(signature)}")

    expected = "\n\n[MCP: filesystem]"
    if signature == expected:
        print(f"[OK] MCP 调用链格式正确")
        return True
    else:
        print(f"[FAIL] 期望: {repr(expected)}, 实际: {repr(signature)}")
        return False


def test_complex_chain():
    """测试复杂调用链"""
    print("\n测试5: 复杂调用链 (Skill -> SubAgent)")
    print("-" * 40)

    tracker = ChainTracker()
    tracker.add("skill", "code-analyzer", 0.95)
    tracker.add("subagent", "complexity-calculator", 0.80)
    signature = tracker.format_signature()

    print(f"签名: {repr(signature)}")

    expected = "\n\n[Skill: code-analyzer → SubAgent: complexity-calculator]"
    if signature == expected:
        print(f"[OK] 复杂调用链格式正确")
        return True
    else:
        print(f"[FAIL] 期望: {repr(expected)}, 实际: {repr(signature)}")
        return False


def test_clear():
    """测试清空调用链"""
    print("\n测试6: 清空调用链")
    print("-" * 40)

    tracker = ChainTracker()
    tracker.add("skill", "test-skill", 0.5)

    print(f"清空前: len={len(tracker)}, is_empty={tracker.is_empty()}")
    tracker.clear()
    print(f"清空后: len={len(tracker)}, is_empty={tracker.is_empty()}")

    if len(tracker) == 0 and tracker.is_empty():
        print(f"[OK] 调用链清空成功")
        return True
    else:
        print(f"[FAIL] 调用链未清空")
        return False


def test_chain_info_format():
    """测试 ChainInfo 格式化"""
    print("\n测试7: ChainInfo 格式化")
    print("-" * 40)

    tests = [
        ("skill", "test-skill", "Skill: test-skill"),
        ("subagent", "test-agent", "SubAgent: test-agent"),
        ("mcp", "test-mcp", "MCP: test-mcp"),
        ("llm", "", "LLM"),
    ]

    all_ok = True
    for source_type, source_name, expected in tests:
        info = ChainInfo(source_type, source_name)
        result = info.format()
        ok = result == expected
        all_ok = all_ok and ok

        status = "[OK]" if ok else "[FAIL]"
        print(f"{status} {source_type}: {repr(result)}")

    return all_ok


def main():
    """运行所有测试"""
    print("=" * 60)
    print("ChainTracker 单元测试")
    print("=" * 60)
    print()

    tests = [
        test_empty_chain,
        test_skill_chain,
        test_subagent_chain,
        test_mcp_chain,
        test_complex_chain,
        test_clear,
        test_chain_info_format,
    ]

    results = [test() for test in tests]

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    print(f"\n通过: {passed}/{total}")

    if passed == total:
        print("\n[OK] 所有测试通过!")
        return True
    else:
        print(f"\n[FAIL] {total - passed} 个测试失败")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
