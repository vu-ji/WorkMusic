"""test_mcp_connection.py — MCP server 接入测试

两种传输验证：
1. in-memory：Client 直连 MCPServer 实例（快速验证工具注册和调用）
2. stdio：真实子进程传输（验证生产路径）

用法：
    python src/test_mcp_connection.py
"""

import asyncio
import sys
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters, stdio_client

sys.path.insert(0, str(Path(__file__).parent))
from mcp_server import server  # noqa: E402


async def test_in_memory() -> None:
    """in-memory 直连：验证工具注册 + 调用。"""
    print("=== 1. in-memory 连接 ===")
    async with Client(server) as client:
        tools_result = await client.list_tools()
        names = [t.name for t in tools_result.tools]
        print(f"  tools: {names}")
        assert "search_catalog" in names, "search_catalog 未注册"

        result = await client.call_tool(
            "search_catalog",
            {"style": "电子摇滚", "bpm_min": 130, "bpm_max": 150, "budget": 3000},
        )
        print(f"  call 返回: content={result.content}")
        print(f"  is_error: {result.is_error}")
        assert result.is_error is False
        print("  ✅ in-memory 通过\n")


async def test_stdio() -> None:
    """stdio 子进程传输：验证生产路径。

    stdio_client 本身是 async context manager，产出 (read, write) 流，
    正好满足 Client 需要的 Transport 协议形状。
    """
    print("=== 2. stdio 传输 ===")
    server_script = str(Path(__file__).parent / "mcp_server.py")
    params = StdioServerParameters(command=sys.executable, args=[server_script])

    async with stdio_client(params) as (read, write):
        from mcp.client.session import ClientSession

        async with ClientSession(read, write) as client:
            # 关键：ClientSession 不自动握手，需显式 initialize()
            await client.initialize()

            tools_result = await client.list_tools()
            print(f"  tools: {[t.name for t in tools_result.tools]}")

            result = await client.call_tool(
                "search_catalog",
                {"style": "电子摇滚", "bpm_min": 130, "bpm_max": 150, "budget": 3000},
            )
            print(f"  call 返回: content={result.content}")
            assert result.is_error is False
            print("  ✅ stdio 通过\n")


async def main() -> None:
    await test_in_memory()
    await test_stdio()
    print("🎉 MCP 接入测试全部通过")


if __name__ == "__main__":
    asyncio.run(main())
