#!/usr/bin/env python3
"""
SubAgent 自动发现功能测试

验证 SubAgent 扫描器能否正确发现和加载 subagents/ 目录下的 Agent。
"""

import sys
import asyncio
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.subagent import SubAgentScanner, SubAgentLoader, SubAgentInput


async def main():
    """主测试函数"""
    print("=" * 60)
    print("SubAgent 自动发现功能测试")
    print("=" * 60)
    print()

    project_root = Path(__file__).parent.parent

    # 测试1: 目录扫描
    print("【测试1】目录扫描测试")
    print(f"项目根目录: {project_root}")
    print(f"扫描目录: {project_root / 'subagents'}")
    print()

    scanner = SubAgentScanner(str(project_root))
    discovered = scanner.scan()

    print(f"发现 {len(discovered)} 个 Agent:")
    for name, info in discovered.items():
        status = "[ENABLED]" if info.enabled else "[DISABLED]"
        print(f"  {status} {name}: {info.description}")
        print(f"       路径: {info.entry_path}")
    print()

    if not discovered:
        print("[WARNING] 未发现任何 Agent，请检查 subagents/ 目录是否存在")
        return

    # 测试2: Agent 加载
    print("【测试2】Agent 加载测试")
    loader = SubAgentLoader(str(project_root))
    loaded = loader.scan_and_load()

    print(f"成功加载 {len(loaded)} 个 Agent:")
    for name, agent in loaded.items():
        print(f"  [OK] {name}: {agent.config.display_name}")
    print()

    # 测试3: can_handle 方法
    print("【测试3】can_handle 置信度测试")
    test_queries = [
        "帮我分析这段代码",
        "提取网页中的邮箱",
        "今天天气怎么样",
        "review my code",
        "scrape this website"
    ]

    for query in test_queries:
        print(f"\n查询: '{query}'")
        input_data = SubAgentInput(query=query)

        scores = []
        for name, agent in loaded.items():
            try:
                score = agent.can_handle(input_data)
                if score > 0:
                    scores.append((name, score))
            except Exception as e:
                print(f"  [WARN] {name} 评估失败: {e}")

        if scores:
            scores.sort(key=lambda x: x[1], reverse=True)
            print(f"  匹配结果:")
            for name, score in scores:
                print(f"    - {name}: {score:.2f}")
        else:
            print(f"  无匹配")

    # 测试4: 执行 Agent
    print("\n【测试4】Agent 执行测试")
    test_agent = loaded.get("code-analyzer")
    if test_agent:
        print(f"测试 Agent: code-analyzer")
        input_data = SubAgentInput(query="分析这段代码: def foo(): pass")

        try:
            output = await test_agent.process(input_data)
            if output.success:
                print(f"[OK] 执行成功")
                print(f"响应预览:")
                lines = output.response.split("\n")[:5]
                for line in lines:
                    print(f"  {line}")
            else:
                print(f"[FAIL] 执行失败: {output.error}")
        except Exception as e:
            print(f"[ERROR] 执行异常: {e}")
    else:
        print("[WARN] code-analyzer Agent 未加载")

    print()
    print("=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
