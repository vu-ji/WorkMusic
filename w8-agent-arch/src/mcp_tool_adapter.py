"""mcp_tool_adapter.py — 让 Agent 通过 MCP 调用工具

把 MCP server 的工具适配成 ReActAgent 需要的 executor 接口
（execute(name, arguments) → {"success": bool, "result"/"error"}）。

这样 ReActAgent 不用改一行代码，只要把 executor 从 W4 手写的
ToolExecutor 换成 MCPToolAdapter，工具调用就走 MCP 协议了。

对比 W4 手写 ToolExecutor：
- W4：executor.execute(name, args) → 直接调本地函数
- MCP：executor.execute(name, args) → JSON-RPC 到 server → 返回

前端类比：手写 executor ≈ 直接 import 函数调用；
MCP 适配器 ≈ 换成 HTTP API 调用（协议变了，接口不变）。
"""

import json
from typing import Any

from mcp import Client


class MCPToolAdapter:
    """MCP 工具适配器：满足 ReActAgent 的 executor 接口。"""

    def __init__(self, client: Client) -> None:
        """初始化。

        Args:
            client: 已连接的 MCP Client（in-memory 或 stdio）
        """
        self._client = client
        self._tools: list[str] = []

    async def list_tools(self) -> list[dict[str, Any]]:
        """列出 MCP server 提供的全部工具（含完整 input_schema）。

        关键：schema 必须传给 LLM——否则模型不知道工具要什么参数，
        会瞎猜参数名（genre/bpm_range），连续失败。
        """
        result = await self._client.list_tools()
        self._tools = [t.name for t in result.tools]
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.input_schema,  # 参数 schema 是 LLM 调用的依据
            }
            for t in result.tools
        ]

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """执行工具（与 W4 ToolExecutor.execute 同构）。

        Returns:
            {"success": True, "result": ...} 或
            {"success": False, "error": ...}
        """
        try:
            result = await self._client.call_tool(tool_name, arguments)
        except Exception as e:
            return {"success": False, "error": f"MCP 调用异常: {e}"}

        if result.is_error:
            return {"success": False, "error": str(result.content)}

        # MCP 返回 TextContent 列表 → 解析 JSON
        texts = []
        for item in result.content:
            text = getattr(item, "text", None)
            if text is not None:
                texts.append(text)

        raw = "\n".join(texts)
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            parsed = raw  # 非 JSON 直接返回文本

        return {"success": True, "result": parsed}
