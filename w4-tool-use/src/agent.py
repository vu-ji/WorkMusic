"""agent.py — W4 Agent Loop：思考 → 行动 → 观察 → 思考

W4 核心交付：手写 Agent Loop，不依赖任何框架。
流程：用户提问 → LLM 决定调工具 or 直接回复 → Executor 执行工具 → LLM 处理结果 → 最终回复。

前端类比：useReducer + async action dispatcher。
dispatch(action) → reducer 更新 state → 如果 action 触发 side effect → 执行 → dispatch 新 action。
"""

import json
import sys
from pathlib import Path
from typing import Any

# 路径补丁，复用 w1-env 的 RouterClient
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "w1-env"))

from src.llm.router import RouterClient
from tool_registry import ToolRegistry
from tool_executor import ToolExecutor, format_error_for_llm

# ============================================================
# System Prompt — 告诉 LLM 它拥有什么工具、怎么用
# ============================================================

def build_system_prompt(tool_schemas: list[dict[str, Any]]) -> str:
    """构造 Agent 的 system prompt，含工具列表和调用约定。

    LLM 收到这个 prompt 后知道：
    1. 你有什么工具可用
    2. 输出格式：{"action": "use_tool", ...} 或 {"action": "reply", ...}
    3. 只能调用列出的工具
    """
    tools_json = json.dumps(tool_schemas, ensure_ascii=False, indent=2)

    return (
        "你是一个音乐版权推荐助手。你可以使用以下工具来检索曲库数据。\n\n"
        f"## 可用工具\n{tools_json}\n\n"
        "## 响应格式\n"
        "你必须输出一个 JSON 对象，从以下两种格式中选择一种：\n\n"
        "1. 调用工具：\n"
        '   {"action": "use_tool", "tool": "工具名", "arguments": {"参数名": "值"}}\n\n'
        "2. 直接回复用户：\n"
        '   {"action": "reply", "content": "你的回答文本"}\n\n'
        "## 规则\n"
        "- 如果需要检索曲库数据才能回答，先调 search_catalog\n"
        "- 如果工具返回空列表，告诉用户暂无匹配数据，不要编造\n"
        "- 如果用户的问题与曲库无关（如打招呼），直接 reply\n"
        "- 不要输出 markdown 代码块，只输出纯 JSON 对象\n"
        "- 如果工具调用参数不完整，根据用户输入推断合理默认值\n"
    )


# ============================================================
# Agent Loop
# ============================================================

class Agent:
    """W4 Agent：手写 think → act → observe 循环。

    用法：
        agent = Agent("light")
        reply = await agent.run("给健身房找 10 首电子摇滚 BGM，BPM 130-150")
    """

    MAX_TURNS = 3  # 最多工具调用 + 回复轮次，防止死循环

    def __init__(self, tier: str = "light") -> None:
        self.client = RouterClient(tier)
        self.registry = ToolRegistry()
        self.registry.register_defaults()
        self.executor = ToolExecutor(self.registry)

    async def run(self, user_query: str) -> dict[str, Any]:
        """执行一轮 Agent 对话。

        Returns:
            {"reply": "...", "turns": N, "tool_calls": [...]}
        """
        system_prompt = build_system_prompt(self.registry.list_schemas())
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query},
        ]

        tool_call_log: list[dict[str, Any]] = []

        for turn in range(self.MAX_TURNS):
            # 1. 调 LLM

            reply, usage = await self.client.chat_sync(messages)

            # 2. 解析 LLM 响应
            action = self._parse_action(reply)
            if action is None:
                # 已调过工具 + 返回自然语言（模型常用行为）→ 当作回复
                if tool_call_log:
                    return {
                        "reply": reply,
                        "turns": turn + 1,
                        "tool_calls": tool_call_log,
                    }
                return {
                    "reply": reply,
                    "turns": turn + 1,
                    "tool_calls": tool_call_log,
                    "error": "LLM 返回了无法解析的格式",
                }

            # 3. 如果 LLM 直接回复 → 结束
            if action["action"] == "reply":
                return {
                    "reply": action["content"],
                    "turns": turn + 1,
                    "tool_calls": tool_call_log,
                }

            # 4. 如果 LLM 调工具 → 执行 → 结果追加到 messages
            if action["action"] == "use_tool":
                result = await self.executor.execute(
                    action["tool"], action["arguments"]
                )
                tool_call_log.append(
                    {
                        "tool": action["tool"],
                        "arguments": action["arguments"],
                        "success": result["success"],
                        "result": result.get("result"),
                        "error": result.get("error"),
                    }
                )

                if result["success"]:
                    # 工具成功 → 把结果告诉 LLM
                    messages.append(
                        {"role": "assistant", "content": reply}
                    )
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                f"工具 {action['tool']} 返回结果：\n"
                                f"{json.dumps(result['result'], ensure_ascii=False)}\n"
                                "请基于以上结果回复用户。"
                            ),
                        }
                    )
                else:
                    # 工具失败 → 把错误告诉 LLM 让它修正
                    messages.append(
                        {"role": "assistant", "content": reply}
                    )
                    messages.append(
                        {
                            "role": "user",
                            "content": format_error_for_llm(
                                action["tool"],
                                action["arguments"],
                                result["error"],
                            ),
                        }
                    )

        # 超过最大轮次仍未得到最终回复
        return {
            "reply": "",
            "turns": self.MAX_TURNS,
            "tool_calls": tool_call_log,
            "error": "超过最大轮次，未能完成对话",
        }

    def _parse_action(self, raw: str) -> dict[str, Any] | None:
        """解析 LLM 返回的 JSON action。

        兼容多种 LLM 输出格式：
        - 纯 JSON: {"action": "use_tool", ...}
        - JSON in code block: ```json\n{...}\n```
        - 带前导/尾部文字的 JSON（尝试提取第一个 {...} 对象）

        Returns:
            {"action": "use_tool", "tool": ..., "arguments": {...}}
            {"action": "reply", "content": "..."}
            None → 解析失败
        """
        text = raw.strip()

        # 去掉 markdown 代码块包装
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if len(lines) >= 3 else text
            text = text.strip()

        # 尝试提取第一个 JSON 对象（兼容 LLM 在 JSON 前后加文字的情况）
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            text = text[start:end]
        except ValueError:
            pass

        try:
            parsed = json.loads(text)
            if "action" not in parsed:
                return None
            if parsed["action"] not in ("use_tool", "reply"):
                return None
            return parsed
        except (json.JSONDecodeError, TypeError):
            return None
