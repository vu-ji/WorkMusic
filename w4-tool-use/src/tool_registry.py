"""tool_registry.py — 工具注册表

管理所有可用工具的注册、查找和 schema 导出。
工具调用流程：LLM 返回 tool_call → Registry 查 tool → Executor 调 tool。

前端类比：Express router——`app.get('/api/search', handler)` 注册路由，
收到请求后 router 匹配路径 → 找到 handler → 执行。
"""

from typing import Any

from tool_schema import TOOLS


class ToolRegistry:
    """工具注册表。

    职责：
    1. 注册工具（schema + 函数绑定）
    2. 按名称查找工具
    3. 导出所有工具的 schema 列表（塞进 system prompt）
    """

    def __init__(self) -> None:
        self._tools: dict[str, dict[str, Any]] = {}

    def register_defaults(self) -> None:
        """从 TOOLS 字典批量注册所有预定义工具。"""
        for name, entry in TOOLS.items():
            self.register(name, entry["schema"], entry["fn"])

    def register(
        self,
        name: str,
        schema: dict[str, Any],
        fn: callable,
    ) -> None:
        """注册一个工具。

        Args:
            name: 工具名，如 "search_catalog"
            schema: JSON Schema 定义
            fn: 实际执行的函数
        """
        if name in self._tools:
            raise ValueError(f"工具 {name} 已注册")
        self._tools[name] = {
            "schema": schema, 
            "fn": fn
        }
        return fn # 方便当装饰器用

    def get(self, name: str) -> dict[str, Any] | None:
        """按名称查找工具。找不到返回 None。"""
        return self._tools.get(name)

    def getSchema(self, name: str) :
        tool = self.get(name)
        return tool["schema"] if tool else None

    def list_schemas(self) -> list[dict[str, Any]]:
        """返回所有工具的 JSON Schema 列表。

        这个列表会塞进 system prompt，告诉 LLM "你可以调用这些工具"。
        """
        return [entry["schema"] for entry in self._tools.values()]

    def list_names(self) -> list[str]:
        """返回所有工具名称列表，用于日志/调试。"""
        return list(self._tools.keys())
