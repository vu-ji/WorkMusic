"""react.py — ReAct 范式（Reasoning + Acting）

W8 核心交付之一。ReAct 让 LLM 交替输出「思考」和「行动」：
    思考 → 行动（调工具）→ 观察（工具结果）→ 思考 → ...

与 W4 Agent Loop 的区别：
- W4：LLM 输出 action → 执行 → 结果回传 → LLM 回复（2 轮内结束）
- ReAct：LLM 可以连续多轮「思考-行动-观察」，直到它认为自己掌握了足够信息
- 关键差异：ReAct 的 prompt 明确要求 LLM 先输出 Thought（推理过程）

前端类比：ReAct ≈ 一个会"边做边想"的异步任务调度器。
- Thought = 每个 tick 里的决策日志
- Action = dispatch 一个 side effect
- Observation = 等到 side effect 的结果
- 循环直到任务完成
"""

import functools
import json
import sys
from pathlib import Path
from typing import Any

# 路径补丁：复用 w1 RouterClient + w4 工具 + w5 重试
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "w1-env"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "w4-tool-use" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "w5-error-retry" / "src"))

from src.llm.router import RouterClient
from retry_controller import RetryController
from tool_registry import ToolRegistry
from tool_executor import ToolExecutor

REACT_SYSTEM_PROMPT = """你是一个能调用工具的 AI 助手。遇到需要数据的问题时，你会交替执行以下步骤：

思考（Thought）：分析当前情况，决定下一步做什么
行动（Action）：调用工具获取数据，格式为 JSON
观察（Observation）：查看工具返回的结果

可用工具：
{schemas}

输出格式（严格 JSON，不要输出 markdown 代码块）：
1. 需要调用工具：
   {{"thought": "你的推理", "action": "工具名", "action_input": {{"参数": "值"}}}}
2. 已经掌握足够信息，可以回答：
   {{"thought": "你的推理", "action": "Final Answer", "action_input": "最终回答"}}

规则：
- 每次只输出一个 JSON 对象
- 如果工具返回空数据，如实告诉用户，不要编造
- 参数根据用户输入推断合理默认值
"""


class ReActAgent:
    """ReAct 范式 Agent。

    用法：
        agent = ReActAgent(tier="light")
        reply = await agent.run("给健身房找 BPM 140 的电子摇滚")
    """

    MAX_STEPS = 6  # ReAct 需要比 W4 更多轮次：可能连续调多个工具才攒够信息

    def __init__(
        self,
        tier: str = "middle",
        executor: Any | None = None,
    ) -> None:
        """初始化。

        Args:
            tier: RouterClient 的 tier（light=7b / heavy=32b）
            executor: 工具执行器，默认用 W4 手写 ToolExecutor；
                传入 MCPToolAdapter 即可切换到 MCP 协议调用
        """
        self.client = RouterClient(tier)
        if executor is not None:
            # 注入外部 executor（如 MCPToolAdapter）
            self.executor = executor
        else:
            # 默认：W4 手写工具
            self.registry = ToolRegistry()
            self.registry.register_defaults()
            self.executor = ToolExecutor(self.registry)
        # 复用 W5：网络/超时错误自动退避重试
        self.retry = RetryController(max_retries=2)

    async def run(self, user_query: str) -> dict[str, Any]:
        """执行一轮 ReAct 循环。

        Returns:
            {"reply": "...", "steps": N, "trace": [每步的 thought/action/observation]}
        """
        if hasattr(self, "registry"):
            schemas = json.dumps(
                self.registry.list_schemas(), ensure_ascii=False, indent=2
            )
        else:
            # MCP 注入模式：用 list_tools 动态获取 schema 信息
            tools = await self.executor.list_tools()
            schemas = json.dumps(tools, ensure_ascii=False, indent=2)
        messages: list[dict[str, str]] = [
            {"role": "system", "content": REACT_SYSTEM_PROMPT.format(schemas=schemas)},
            {"role": "user", "content": user_query},
        ]
        trace: list[dict[str, Any]] = []

        for step in range(self.MAX_STEPS):
            # 1. LLM 输出（思考 + 行动）
            reply, _ = await self.client.chat_sync(messages)
            parsed = self._parse_step(reply)

            if parsed is None:
                # 解析失败 → 把提示追加回去让 LLM 重来
                messages.append({"role": "assistant", "content": reply})
                messages.append({
                    "role": "user",
                    "content": "你的输出无法解析，请重新输出严格 JSON（不要 markdown 代码块）。",
                })
                continue

            thought = parsed.get("thought", "")
            action = parsed["action"]
            action_input = parsed.get("action_input", {})

            # 2. Final Answer → 结束
            if action == "Final Answer":
                trace.append({"thought": thought, "action": "Final Answer"})
                return {
                    "reply": action_input,
                    "steps": step + 1,
                    "trace": trace,
                }

            # 3. 执行工具（W4 executor + W5 retry 组合）
            exec_fn = functools.partial(self.executor.execute, action)
            result = await self.retry.try_with_retry(
                exec_fn, arguments=action_input
            )

            # 4. 观察结果 → 追加到 messages，继续循环
            if result["success"]:
                observation = json.dumps(result["result"], ensure_ascii=False)
            else:
                observation = f"工具执行失败: {result.get('error', '')}"

            trace.append({
                "thought": thought,
                "action": action,
                "action_input": action_input,
                "observation": observation,
            })
            messages.append({"role": "assistant", "content": reply})
            messages.append({"role": "user", "content": f"观察: {observation}"})

        # 5. 超过最大步数
        return {
            "reply": "",
            "steps": self.MAX_STEPS,
            "trace": trace,
            "error": "超过最大步数，未能完成",
        }

    def _parse_step(self, reply: str) -> dict[str, Any] | None:
        """解析 LLM 输出。兼容 markdown 包装和前后文字。

        Returns:
            {"thought": str, "action": str, "action_input": ...}
            None → 解析失败
        """
        text = reply.strip()

        # 去 markdown 代码块
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if len(lines) >= 3 else text
            text = text.strip()

        # 提取第一个 { 到最后一个 }
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            text = text[start:end]
        except ValueError:
            return None

        try:
            parsed = json.loads(text)
            if "action" not in parsed:
                return None
            return parsed
        except (json.JSONDecodeError, TypeError):
            return None
