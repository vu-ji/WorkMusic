"""plan_execute.py — Plan-Execute 范式

W8 核心交付之二。与 ReAct 的区别：

ReAct：边想边做——每步先 Thought 再 Action，遇到问题现场调整
Plan-Execute：先计划再执行——第一步让 LLM 生成完整计划，
    然后逐步执行计划中的每个任务，执行完对比计划看是否完成

适用场景：
- ReAct：任务简单、路径不确定、需要探索（如"帮我查一下..."）
- Plan-Execute：任务复杂、步骤明确、需要规划（如"写一个 RAG 系统的架构文档"）

前端类比：
- ReAct ≈ 事件循环里每个 tick 决策（边跑边改）
- Plan-Execute ≈ 先写 TODO list 再执行（任务拆解 + 逐个完成）
"""

import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "w1-env"))

from src.llm.router import RouterClient

PLAN_PROMPT = """你是任务规划器。把用户的复杂任务拆解成有序的步骤列表。

用户任务：{task}

输出严格 JSON（不要 markdown 代码块）：
{{"plan": ["步骤1", "步骤2", "步骤3"]}}

规则：
- 3-5 个步骤，每步是独立可执行的原子任务
- 步骤要具体（"检索曲库中 BPM 130-150 的电子摇滚"而不是"找歌"）
- 步骤之间按依赖顺序排列
"""

EXECUTE_PROMPT = """你是执行器。按照计划逐步执行，当前进度：

计划：
{plan}

已完成：
{completed}

当前任务：{current_task}

执行当前任务。如果任务完成输出：
{{"done": true, "result": "任务结果"}}
如果无法完成输出：
{{"done": false, "result": "遇到的阻碍"}}
输出严格 JSON（不要 markdown 代码块）。
"""


class PlanExecuteAgent:
    """Plan-Execute 范式 Agent。

    用法：
        agent = PlanExecuteAgent(tier="light")
        reply = await agent.run("写一个 RAG 系统架构设计")
    """

    def __init__(self, tier: str = "middle") -> None:
        self.client = RouterClient(tier)

    async def run(self, task: str) -> dict[str, Any]:
        """执行 Plan-Execute。

        Returns:
            {"plan": [...], "results": [...], "reply": "汇总回答"}
        """
        # 1. 生成计划
        plan = await self._make_plan(task)
        if not plan:
            return {"plan": [], "results": [], "reply": "", "error": "计划生成失败"}

        # 2. 逐条执行
        results: list[dict[str, Any]] = []
        completed: list[str] = []

        for step_idx, step in enumerate(plan):
            result = await self._execute_step(plan, completed, step)
            results.append({"step": step, **result})
            if result.get("done"):
                completed.append(step)

        # 3. 汇总
        done_count = sum(1 for r in results if r.get("done"))
        summary = (
            f"计划共 {len(plan)} 步，完成 {done_count} 步。\n"
            + "\n".join(
                f"- {r['step']}: {'✅ ' + str(r.get('result', ''))[:80] if r.get('done') else '❌ ' + str(r.get('result', ''))[:80]}"
                for r in results
            )
        )
        return {"plan": plan, "results": results, "reply": summary}

    async def _make_plan(self, task: str) -> list[str] | None:
        """生成计划。"""
        prompt = PLAN_PROMPT.format(task=task)
        messages = [{"role": "user", "content": prompt}]
        reply, _ = await self.client.chat_sync(messages)
        return self._parse_plan(reply)

    async def _execute_step(
        self,
        plan: list[str],
        completed: list[str],
        current_task: str,
    ) -> dict[str, Any]:
        """执行单个步骤。"""
        plan_str = "\n".join(f"{i+1}. {s}" for i, s in enumerate(plan))
        completed_str = "\n".join(completed) if completed else "（暂无）"
        prompt = EXECUTE_PROMPT.format(
            plan=plan_str,
            completed=completed_str,
            current_task=current_task,
        )
        messages = [{"role": "user", "content": prompt}]

        # 解析失败重试一次
        for _ in range(2):
            reply, _ = await self.client.chat_sync(messages)
            parsed = self._parse_execution(reply)
            if parsed is not None:
                return parsed
        return {"done": False, "result": "解析失败"}

    def _parse_plan(self, reply: str) -> list[str] | None:
        """解析 LLM 生成的计划 {"plan": [...]}。

        容错：qwen2.5:7b 常把数组元素写成 {"步骤N": "内容"}（非法 JSON），
        先用正则剥掉 "步骤N": 前缀修复，再解析。
        """
        repaired = self._repair_plan_json(reply)
        parsed = self._parse_json(repaired)
        if parsed is None or "plan" not in parsed:
            return None
        plan = parsed["plan"]
        if not isinstance(plan, list) or not plan:
            return None
        return [str(s) for s in plan]

    def _repair_plan_json(self, reply: str) -> str:
        """修复 qwen2.5:7b 的非法 JSON：数组元素写成 {"步骤N": "内容"}。

        模式：["步骤1": "内容", "步骤2": "内容"] → ["内容", "内容"]
        只匹配 "步骤N": 前缀，不会误伤正常字符串。
        """
        return re.sub(r'"步骤\d+"\s*:\s*', '', reply)

    def _parse_execution(self, reply: str) -> dict[str, Any] | None:
        """解析执行结果 {"done": bool, "result": str}。"""
        parsed = self._parse_json(reply)
        if parsed is None or "done" not in parsed:
            return None
        return {
            "done": bool(parsed["done"]),
            "result": str(parsed.get("result", "")),
        }

    def _parse_json(self, reply: str) -> dict[str, Any] | None:
        """通用 JSON 解析：剥 markdown → 提取 {} → json.loads。"""
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
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return None
