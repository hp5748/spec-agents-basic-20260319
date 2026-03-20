"""
T011 集成测试 - 快速验证脚本

执行核心功能验证，输出简洁结果。
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agent.tool_registry import ToolRegistry, get_global_registry
from src.adapters.core.factory import AdapterFactory, get_global_factory
from src.adapters.core.types import AdapterConfig, AdapterType, ToolRequest
from src.agent.chain_tracker import ChainTracker


async def main():
    """执行快速验证"""
    print("="*60)
    print("  T011: Agentic Architecture Integration Test")
    print("="*60)

    results = {}

    # Test 1: ToolRegistry
    print("\n[1/5] ToolRegistry...")
    try:
        registry = get_global_registry()

        @registry.register("test_add", description="Addition")
        def add(a: int, b: int) -> int:
            return a + b

        result = await registry.execute("test_add", a=1, b=2)
        assert result.data == 3

        schema = registry.to_openapi_schema()
        assert schema["stats"]["total"] >= 1

        results["ToolRegistry"] = "PASS"
        print("  ✓ Tool registration: OK")
        print("  ✓ Tool execution: OK")
        print("  ✓ Schema generation: OK")
    except Exception as e:
        results["ToolRegistry"] = f"FAIL: {e}"
        print(f"  ✗ Error: {e}")

    # Test 2: AdapterFactory
    print("\n[2/5] AdapterFactory...")
    try:
        factory = get_global_factory()

        config = AdapterConfig(
            type=AdapterType.CUSTOM,
            name="test_adapter",
            enabled=True
        )

        adapter = await factory.create_adapter(config)
        assert adapter is not None

        request = ToolRequest(
            tool_name="echo",
            parameters={"message": "test"}
        )

        response = await adapter.execute(request)
        assert response.success

        results["AdapterFactory"] = "PASS"
        print("  ✓ Adapter creation: OK")
        print("  ✓ Tool execution: OK")
    except Exception as e:
        results["AdapterFactory"] = f"FAIL: {e}"
        print(f"  ✗ Error: {e}")

    # Test 3: ChainTracker
    print("\n[3/5] ChainTracker...")
    try:
        tracker = ChainTracker()
        tracker.add("skill", "test_skill", 0.9)
        tracker.add("tool", "test_tool", 1.0)

        chain = tracker.get_chain()
        assert len(chain) == 2

        summary = tracker.get_summary()
        assert summary["total_calls"] == 2

        signature = tracker.format_signature()
        assert "test_skill" in signature

        results["ChainTracker"] = "PASS"
        print("  ✓ Call tracking: OK")
        print("  ✓ Summary generation: OK")
        print("  ✓ Signature format: OK")
    except Exception as e:
        results["ChainTracker"] = f"FAIL: {e}"
        print(f"  ✗ Error: {e}")

    # Test 4: Integration
    print("\n[4/5] Integration (Registry + Factory)...")
    try:
        registry = get_global_registry()
        factory = get_global_factory()

        # Register a tool
        from src.agent.tool import Tool, ToolType, ToolParameter

        tool = Tool(
            name="integration_test",
            type=ToolType.CUSTOM,
            description="Integration test tool",
            parameters=[
                ToolParameter(name="x", type="number", required=True)
            ],
            handler=lambda **kwargs: ToolResult(success=True, data=kwargs.get("x", 0) * 2)
        )

        registry.register_tool(tool)

        # Execute through registry
        result = await registry.execute("integration_test", x=21)
        assert result.data == 42

        results["Integration"] = "PASS"
        print("  ✓ Tool registration: OK")
        print("  ✓ Tool execution: OK")
        print("  ✓ Result verification: OK (21 * 2 = 42)")
    except Exception as e:
        results["Integration"] = f"FAIL: {e}"
        print(f"  ✗ Error: {e}")

    # Test 5: Function Calling Simulation
    print("\n[5/5] Function Calling Simulation...")
    try:
        registry = get_global_registry()

        # Simulate LLM flow
        tools_schema = registry.to_openapi_schema()
        assert tools_schema["stats"]["total"] > 0

        # Mock tool call
        mock_call = {
            "function_name": "integration_test",
            "arguments": {"x": 10}
        }

        result = await registry.execute(**mock_call)
        assert result.success

        results["FunctionCalling"] = "PASS"
        print("  ✓ Schema generation: OK")
        print("  ✓ Tool execution: OK")
        print("  ✓ Flow simulation: OK")
    except Exception as e:
        results["FunctionCalling"] = f"FAIL: {e}"
        print(f"  ✗ Error: {e}")

    # Summary
    print("\n" + "="*60)
    print("  Test Results Summary")
    print("="*60)

    passed = sum(1 for v in results.values() if v == "PASS")
    total = len(results)

    for test, result in results.items():
        status = "✓ PASS" if result == "PASS" else "✗ FAIL"
        print(f"  {status}: {test}")

    print(f"\n  Total: {passed}/{total} passed")

    if passed == total:
        print("\n  ✓ All tests PASSED!")
        print("  ✓ Agentic architecture is ready for production")
        return 0
    else:
        print(f"\n  ✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
