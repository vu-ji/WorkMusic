"""tool_executor.py — 工具执行器

W4 核心模块。接收 LLM 返回的 tool_call，完成四步：
1. 查注册表 → 工具存在？
2. 校验参数 → 参数符合 schema？
3. 执行函数 → 拿到结果
4. 如果失败 → 把错误信息格式化发给 LLM 重试

前端类比：Express middleware 链——请求进来 → 路由匹配 → 参数校验 → handler → 响应。
校验失败不是 500——是 400 + 告诉调用方 "你哪个字段错了"，LLM 修完再重试。
"""

import asyncio
import inspect
import json
from typing import Any


class ToolExecutor:
    """工具执行器。

    用法：
        executor = ToolExecutor(registry)
        result = executor.execute("search_catalog", {"style": "电子", "bpm_min": 120})
    """

    def __init__(self, registry) -> None:
        self.registry = registry

    async def execute(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """执行一个工具调用。同步和异步工具函数都支持。

        Args:
            tool_name: 工具名，如 "search_catalog"
            arguments: LLM 传来的参数字典

        Returns:
            {"success": True, "result": [...]} 或
            {"success": False, "error": "参数 bpm_min 必须是整数，收到 abc"}
        """
        # 1. 查注册表
        tool = self.registry.get(tool_name)
        if tool is None:
            return {"success": False, "error": f"未知工具: {tool_name}"}

        # 2. 校验参数
        error = self.validate_params(arguments, tool["schema"])
        if error is not None:
            return {"success": False, "error": error}

        # 3. 执行（兼容同步和异步工具函数）
        try:
            fn = tool["fn"]
            if inspect.iscoroutinefunction(fn):
                result = await fn(**arguments)
            else:
                result = fn(**arguments)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": f"工具执行异常: {e}"}

    def validate_params(
        self,
        arguments: dict[str, Any],
        schema: dict[str, Any],
    ) -> str | None:
        """校验参数是否符合 schema。

        Returns:
            None → 校验通过
            str → 错误描述（格式化的错误信息，方便 LLM 理解并修正）
        """
        properties = schema["parameters"]["properties"]
        required_fields = schema["parameters"]["required"]

        # 检查缺失的必填参数
        for field in required_fields:
            if field not in arguments:
                missing = [f for f in required_fields if f not in arguments]
                return f"缺少必填参数: {', '.join(missing)}，请补充后重试"

        # 检查是否有未知参数（不在 schema 定义中）
        for key in arguments:
            if key not in properties:
                return f"未知参数 '{key}'，允许的参数: {', '.join(properties.keys())}"

        # 类型映射
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
        }

        # 检查每个参数的类型
        for key, value in arguments.items():
            expected_json_type = properties[key]["type"]
            expected_py_type = type_map.get(expected_json_type)
            if expected_py_type is None:
                return f"参数 '{key}' 的类型 '{expected_json_type}' 不支持"

            # 特殊处理 integer：bool 是 int 子类（isinstance(True,int) == True）
            # 必须用 type() 精确匹配，否则 True 会通过 integer 校验
            if expected_json_type == "integer" and type(value) is not int:
                return (
                    f"参数 '{key}' 必须是整数（integer），"
                    f"收到 {type(value).__name__}: {value}"
                )
            elif expected_json_type == "number":
                if type(value) is bool or type(value) not in (int, float):
                    return (
                        f"参数 '{key}' 必须是数字（number），"
                        f"收到 {type(value).__name__}: {value}"
                    )
            elif not isinstance(value, expected_py_type):
                return (
                    f"参数 '{key}' 必须是 {expected_json_type}，"
                    f"收到 {type(value).__name__}: {value}"
                )

        return None


def format_error_for_llm(
    tool_name: str,
    arguments: dict[str, Any],
    error: str,
) -> str:
    """把校验错误格式化成 LLM 能理解的提示。

    这段提示会追加到对话历史里，LLM 看到后修正参数再重试。

    Args:
        tool_name: 工具名
        arguments: LLM 原本传的参数
        error: validate_params 返回的错误描述

    Returns:
        格式化的错误提示文本
    """
    return (
        f"工具 {tool_name} 调用失败。\n"
        f"传入参数：{json.dumps(arguments, ensure_ascii=False)}\n"
        f"错误原因：{error}\n"
        "请修正参数后重新调用。"
    )
