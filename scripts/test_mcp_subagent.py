#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MCP 和 SubAgent 模块快速测试脚本

用法:
    python scripts/test_mcp_subagent.py
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


async def test_mcp_config():
    """测试 MCP 配置加载"""
    print("\n" + "="*60)
    print("测试 MCP 配置加载")
    print("="*60)

    from mcp.config import MCPConfigLoader

    loader = MCPConfigLoader(str(project_root))
    config = loader.load()

    print(f"\n✓ 配置加载成功")
    print(f"  - 用户级服务器: {len(config.user_level)} 个")
    print(f"  - 项目级服务器: {len(config.project_level)} 个")
    print(f"  - 总服务器数: {len(config.get_all_servers())} 个")

    print("\n服务器列表:")
    for name, server in config.get_all_servers().items():
        status = "禁用" if server.disabled else "启用"
        print(f"  - {name}: {server.transport} ({status})")

    return True


async def test_subagent_config():
    """测试 SubAgent 配置加载"""
    print("\n" + "="*60)
    print("测试 SubAgent 配置加载")
    print("="*60)

    from subagent.config import SubAgentConfigLoader

    loader = SubAgentConfigLoader(str(project_root))
    config = loader.load()

    print(f"\n✓ 配置加载成功")
    print(f"  - 配置的 Agent 数: {len(config)} 个")

    print("\nAgent 列表:")
    for name, agent in config.items():
        status = "禁用" if not agent.enabled else "启用"
        print(f"  - {name}: {status}")
        if agent.triggers:
            keywords = agent.triggers.get("keywords", [])
            if keywords:
                print(f"    关键词: {', '.join(keywords[:3])}")

    return True


async def test_mcp_client():
    """测试 MCP 客户端（不实际连接）"""
    print("\n" + "="*60)
    print("测试 MCP 客户端初始化")
    print("="*60)

    from mcp.client import MCPClient

    client = MCPClient(str(project_root))

    # 不实际初始化（避免启动进程），只测试配置加载
    config_loader = client._loader
    config = config_loader.load()

    print(f"\n✓ 客户端创建成功")
    print(f"  - 可用服务器: {len(config.get_all_servers())} 个")

    # 测试服务器列表方法
    servers = config_loader.list_available_servers()
    print(f"  - 服务器列表: {', '.join(servers)}")

    return True


async def test_subagent_orchestrator():
    """测试 SubAgent 编排器（不实际加载）"""
    print("\n" + "="*60)
    print("测试 SubAgent 编排器初始化")
    print("="*60)

    from subagent.orchestrator import SubAgentOrchestrator

    orchestrator = SubAgentOrchestrator(str(project_root))

    # 不实际初始化（避免加载不存在的 Agent），只测试配置加载
    config_loader = orchestrator._loader
    config = config_loader.load()

    print(f"\n✓ 编排器创建成功")
    print(f"  - 配置的 Agent: {len(config)} 个")

    # 测试 Agent 列表方法
    agents = config_loader.list_available_agents()
    print(f"  - 可用 Agent: {', '.join(agents) if agents else '无'}")

    return True


async def test_json_schema_validation():
    """测试配置文件 JSON Schema 验证"""
    print("\n" + "="*60)
    print("测试配置文件 JSON Schema")
    print("="*60)

    import json

    # 测试 MCP 配置
    mcp_config_path = project_root / ".claude" / "mcp.json"
    with open(mcp_config_path, encoding="utf-8") as f:
        mcp_data = json.load(f)

    print(f"\n✓ MCP 配置 JSON 格式有效")
    print(f"  - Schema: {mcp_data.get('$schema', 'N/A')}")
    print(f"  - 服务器数: {len(mcp_data.get('mcpServers', {}))}")

    # 测试 Agents 配置
    agents_config_path = project_root / ".claude" / "agents.json"
    with open(agents_config_path, encoding="utf-8") as f:
        agents_data = json.load(f)

    print(f"\n✓ Agents 配置 JSON 格式有效")
    print(f"  - Schema: {agents_data.get('$schema', 'N/A')}")
    print(f"  - Agent 数: {len(agents_data.get('subagents', {}))}")

    return True


async def test_imports():
    """测试所有模块导入"""
    print("\n" + "="*60)
    print("测试模块导入")
    print("="*60)

    modules = [
        ("mcp.config", "MCPConfigLoader"),
        ("mcp.client", "MCPClient"),
        ("mcp.transport.stdio", "STDIOTransport"),
        ("mcp.transport.http", "HTTPTransport"),
        ("subagent.config", "SubAgentConfigLoader"),
        ("subagent.base_agent", "SubAgent"),
        ("subagent.orchestrator", "SubAgentOrchestrator"),
    ]

    for module_name, class_name in modules:
        try:
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)
            print(f"  [OK] {module_name}.{class_name}")
        except Exception as e:
            print(f"  [FAIL] {module_name}.{class_name}: {e}")
            return False

    print(f"\n[OK] 所有模块导入成功")
    return True


async def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("MCP 和 SubAgent 模块测试")
    print("="*60)

    tests = [
        ("模块导入", test_imports),
        ("JSON Schema", test_json_schema_validation),
        ("MCP 配置", test_mcp_config),
        ("SubAgent 配置", test_subagent_config),
        ("MCP 客户端", test_mcp_client),
        ("SubAgent 编排器", test_subagent_orchestrator),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result, None))
        except Exception as e:
            results.append((test_name, False, str(e)))
            print(f"\n[FAIL] 测试失败: {e}")

    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)

    passed = sum(1 for _, result, _ in results if result)
    failed = len(results) - passed

    for test_name, result, error in results:
        status = "[OK] 通过" if result else "[FAIL] 失败"
        print(f"{status} - {test_name}")
        if error:
            print(f"    错误: {error}")

    print(f"\n总计: {passed}/{len(results)} 通过")

    if failed > 0:
        print(f"\n[WARN] 有 {failed} 个测试失败")
        return 1
    else:
        print(f"\n[OK] 所有测试通过")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
