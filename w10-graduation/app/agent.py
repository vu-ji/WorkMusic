"""app/agent.py — 毕业项目 Agent 决策层

整合 W8 ReAct + W9 图引擎思想的升级版。

设计（借鉴 LangGraph 状态机思想）：
- 状态（state）：{messages, memory, tool_results} 在节点间流转
- 节点（node）：decide（LLM 决策）→ act（执行工具）→ observe（处理结果）
- 循环：直到 Final Answer 或 MAX_STEPS

与 W8 ReAct 的区别：
1. 支持多个工具注册（search_catalog + knowledge_search）
2. 接入短期+长期记忆（W8 memory.py）
3. 工具执行带重试（W5 RetryController）
4. 状态显式管理（借鉴 graphon VariablePool 思想）
"""

import functools
import json
import sys
from pathlib import Path
from typing import Any

# 路径补丁：复用 W1-W8 组件
_WORKMUSIC = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_WORKMUSIC / "w1-env"))
sys.path.insert(0, str(_WORKMUSIC / "w5-error-retry" / "src"))
sys.path.insert(0, str(_WORKMUSIC / "w8-agent-arch" / "src"))

from src.llm.router import RouterClient
from retry_controller import RetryController

REACT_SYSTEM_PROMPT = """你是一个能调用工具的 AI 助手。遇到需要数据的问题时，你会交替执行以下步骤：

思考（Thought）：分析当前情况，决定下一步做什么
行动（Action）：调用工具获取数据，格式为 JSON
观察（Observation）：查看工具返回的结果

可用工具：
{schemas}

用户长期记忆（跨会话偏好，回答时参考）：
{long_memory}

输出格式（严格 JSON，不要输出 markdown 代码块）：
1. 需要调用工具：
   {{"thought": "你的推理", "action": "工具名", "action_input": {{"参数": "值"}}}}
2. 已经掌握足够信息，可以回答：
   {{"thought": "你的推理", "action": "Final Answer", "action_input": "最终回答"}}

规则：
- 每次只输出一个 JSON 对象
- 如果工具返回空数据，如实告诉用户，不要编造
- 参数根据用户输入推断合理默认值
- 涉及具体歌曲/风格/价格的问题 → 必须调用 search_catalog 查询曲库
- 涉及音乐知识/场景分析的问题 → 必须调用 knowledge_search 查询知识库
- 不要凭记忆回答应该查工具的问题——先查工具，用工具结果回答
"""


class GraduationAgent:
    """毕业项目 Agent：ReAct 决策 + 多工具 + 记忆。"""

    MAX_STEPS = 8  # 多工具场景需要更多轮次（可能先查曲库再查知识库）

    def __init__(
        self,
        tier: str = "middle",
        tools: dict[str, Any] | None = None,
        short_memory=None,
        long_memory=None,
    ) -> None:
        """初始化。"""
        self.client = RouterClient(tier)
        self.tools = tools or {}
        self.short_memory = short_memory
        self.long_memory = long_memory
        self.retry = RetryController(max_retries=2)

    def _tool_schemas(self) -> str:
        """把工具注册表转成 LLM 可读的 schema 描述。"""
        schemas = []
        for name, meta in self.tools.items():
            schema = meta.get("schema", {})
            props = schema.get("properties", {})
            desc = []
            for pname, pmeta in props.items():
                desc.append(f"  {pname} ({pmeta.get('type', '?')}): {pmeta.get('description', '')}")
            schemas.append(
                f"- {name}: {schema.get('description', '')}\n"
                + "\n".join(desc)
            )
        return "\n".join(schemas) if schemas else "（无工具）"

    def _long_memory_text(self) -> str:
        """把长期记忆转成文本注入 system prompt。"""
        if self.long_memory is None:
            return "（无）"
        facts = self.long_memory.recall()
        if not facts:
            return "（无）"
        lines = []
        for f in facts:
            try:
                val = json.dumps(f.get("value"), ensure_ascii=False)
            except (TypeError, ValueError):
                val = str(f.get("value"))
            lines.append(f"- {f.get('key')}: {val}")
        return "\n".join(lines)

    async def run(self, user_query: str) -> dict[str, Any]:
        """执行一轮对话。

        Returns:
            {"reply": "...", "steps": N, "trace": [...]}
        """
        # 1. 构造 system prompt（工具 schema + 长期记忆）
        system_prompt = REACT_SYSTEM_PROMPT.format(
            schemas=self._tool_schemas(),
            long_memory=self._long_memory_text(),
        )

        # 2. 短期记忆：已有历史 + 新 query
        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        if self.short_memory is not None:
            messages.extend(self.short_memory.get_messages())
        messages.append({"role": "user", "content": user_query})

        trace: list[dict[str, Any]] = []

        # 3. ReAct 循环
        for step in range(self.MAX_STEPS):
            reply, _ = await self.client.chat_sync(messages)
            parsed = self._parse_step(reply)

            if parsed is None:
                messages.append({"role": "assistant", "content": reply})
                messages.append({
                    "role": "user",
                    "content": "你的输出无法解析，请重新输出严格 JSON（不要 markdown 代码块）。",
                })
                continue

            thought = parsed.get("thought", "")
            action = parsed["action"]
            action_input = parsed.get("action_input", {})

            # Final Answer → 结束 + 更新记忆
            if action == "Final Answer":
                trace.append({"thought": thought, "action": "Final Answer"})
                # 更新短期记忆
                if self.short_memory is not None:
                    self.short_memory.add_user(user_query)
                    self.short_memory.add_assistant(str(action_input))
                # 提取长期偏好（LLM 抽取，写入长期记忆）
                if self.long_memory is not None:
                    prefs = await self._extract_preferences(trace)
                    for key, value in prefs:
                        self.long_memory.remember(key, value)
                return {
                    "reply": action_input,
                    "steps": step + 1,
                    "trace": trace,
                }

            # 执行工具（带 W5 重试）
            tool_meta = self.tools.get(action)
            if tool_meta is None:
                observation = f"未知工具: {action}，可用: {list(self.tools.keys())}"
                success = False
            else:
                handler = tool_meta["handler"]
                exec_fn = functools.partial(self._safe_call, handler, action_input)
                result = await self.retry.try_with_retry(exec_fn)
                if result["success"]:
                    observation = json.dumps(result["result"], ensure_ascii=False)
                    success = True
                else:
                    observation = f"工具执行失败: {result.get('error', '')}"
                    success = False

            trace.append({
                "thought": thought,
                "action": action,
                "action_input": action_input,
                "observation": observation,
                "success": success,
            })
            messages.append({"role": "assistant", "content": reply})
            messages.append({"role": "user", "content": f"观察: {observation}"})

        # 超步数
        return {
            "reply": "",
            "steps": self.MAX_STEPS,
            "trace": trace,
            "error": "超过最大步数，未能完成",
        }

    async def _safe_call(self, handler, arguments: dict) -> dict[str, Any]:
        """包装工具调用：兼容同步/异步 handler，返回值可能非 dict。"""
        result = handler(arguments)
        if hasattr(result, "__await__"):
            result = await result
        if isinstance(result, dict):
            return result  # handler 自带 {"success", ...} 结构
        return {"success": True, "result": result}  # 裸值（list/str）包一层

    def _parse_step(self, reply: str) -> dict[str, Any] | None:
        """解析 LLM 输出（兼容 markdown + 前后文字）。"""
        text = reply.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if len(lines) >= 3 else text
            text = text.strip()
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

    PREFERENCE_PROMPT = """你是用户偏好分析器。从下面的对话中提取可长期记忆的用户偏好。

对话记录：
{trace_text}

只提取明确的、跨会话有用的偏好（如音乐风格、预算、使用场景）。
输出严格 JSON（不要 markdown 代码块）：
{{"preferences": [{{"key": "偏好名", "value": "偏好值"}}]}}
如果没有偏好，输出 {{"preferences": []}}
"""

    async def _extract_preferences(self, trace: list[dict]) -> list[tuple[str, Any]]:
        """从对话中提取可长期记忆的用户偏好（LLM 抽取）。

        在 run() 的 Final Answer 时调用，提取结果写入长期记忆。
        失败时返回空列表（不影响主流程）。
        """
        # 只看工具调用步骤的 thought + observation（含用户原始 query 的上下文）
        trace_text = json.dumps(trace, ensure_ascii=False)[:800]
        prompt = self.PREFERENCE_PROMPT.format(trace_text=trace_text)
        try:
            reply, _ = await self._run_pref_extraction(prompt)
            parsed = self._parse_step(reply)
            if parsed is None:
                return []
            prefs_raw = parsed.get("preferences", [])
            return [
                (str(p.get("key", "")), p.get("value", ""))
                for p in prefs_raw
                if isinstance(p, dict) and p.get("key")
            ]
        except Exception:
            return []

    async def _run_pref_extraction(self, prompt: str) -> tuple[str, Any]:
        """偏好抽取的 LLM 调用。"""
        reply, usage = await self.client.chat_sync(
            [{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        return reply, usage
