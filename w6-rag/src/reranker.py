"""reranker.py — LLM 重排序（W7 实现）

检索出的 top_k 候选里，向量和 BM25 都有噪声。
重排序 = 用更强的模型对候选逐条精排。

为什么选 LLM 打分而不是 cross-encoder（bge-reranker）？
- 零新依赖：Ollama 没有 bge-reranker，方案 A 要拉新模型
- 理解力强：cross-encoder 只看 token 匹配，LLM 能理解语义（"这首歌适不适合健身房"）
- 候选少：top_k 3-5 条，逐条打分成本可接受（每条 ~200 token）
- 可解释：LLM 能输出打分理由，不只是分数

逐条打分 vs 批量排序：
- 逐条打分（本实现）：N 次 LLM 调用，每条独立评估 → 可解释、分数可比、单条失败不影响其他
- 批量排序：1 次调用让 LLM 排全部 → 便宜但 LLM 容易"端水"（不给低分）、输出不稳定
- W7 选逐条：候选少所以成本可控，且理由可回传做日志/调试

用法：
    reranker = LLMReranker(tier="light")
    results = await reranker.rerank("适合健身房的电子摇滚", candidates)
"""

import json
import sys
from pathlib import Path
from typing import Any

# 路径补丁：复用 w1-env 的 RouterClient 和 w5 的 RetryController
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "w1-env"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "w5-error-retry" / "src"))

from src.llm.router import RouterClient
from retry_controller import RetryController

RERANK_PROMPT = """你是音乐版权审核专家。判断候选歌曲与用户需求的匹配程度。

用户需求：{query}

候选歌曲：
{doc}

请从 0-10 打分（10 = 完全匹配），并给出理由。
只输出 JSON，格式：
{{"score": 0-10 的整数, "reason": "一句话理由"}}
"""


class LLMReranker:
    """基于 LLM 打分的重排序器。"""

    def __init__(
        self,
        tier: str = "light",
        temperature: float = 0.0,
        retry_count: int = 2,
    ) -> None:
        """初始化。

        Args:
            tier: RouterClient 的 tier（light=7b / heavy=32b）
            temperature: 打分要确定性 → 0.0（避免随机分数）
            retry_count: 解析失败时的重试次数
        """
        self.client = RouterClient(tier)
        self.temperature = temperature
        self.retry_count = retry_count
        # W5 组件复用：网络/超时错误 → RetryController 自动退避重试
        self.retry = RetryController(max_retries=2)

    async def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """对候选逐条打分重排。

        Args:
            query: 原始查询
            candidates: retrieve() 返回的候选列表（含 id/document/metadata/score）

        Returns:
            按 LLM 分数降序的列表，每条附加：
            - rerank_score: LLM 打的 0-10 分
            - rerank_reason: 打分理由
            - 原始 score 保留（对比重排前后用）
        """
        if not candidates:
            return []

        # 1. 逐条打分（候选少，串行即可；并行会打乱顺序且同时打多个模型请求）
        scored = []
        for cand in candidates:
            result = await self._score_one(query, cand)
            if result is not None:
                scored.append(result)

        # 2. 按 LLM 分数降序
        scored.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored

    async def _score_one(
        self,
        query: str,
        candidate: dict[str, Any],
    ) -> dict[str, Any] | None:
        """对单条候选打分。解析失败返回 None（该候选被丢弃）。

        Returns:
            候选 + rerank_score + rerank_reason；解析失败 → None
        """
        prompt = RERANK_PROMPT.format(
            query=query,
            doc=candidate.get("document", ""),
        )
        messages = [{"role": "user", "content": prompt}]

        # 第一层（网络层）：LLM 调用交给 RetryController——瞬时错误自动退避重试
        async def call_llm():
            reply, _ = await self.client.chat_sync(
                messages, temperature=self.temperature
            )
            return reply

        for attempt in range(self.retry_count + 1):
            # 网络/超时错误 → RetryController 处理（重试耗尽返回 success=False）
            result = await self.retry.try_with_retry(call_llm)
            if not result["success"]:
                return None

            # 第二层（语义层）：解析失败 → 重新生成（LLM 输出格式问题，非网络问题）
            parsed = self._parse_score(result["result"])
            if parsed is not None:
                return {
                    **candidate,
                    "rerank_score": parsed["score"],
                    "rerank_reason": parsed.get("reason", ""),
                }
            # 解析失败 → 再来一轮（最多 retry_count 次）
        return None

    def _parse_score(self, reply: str) -> dict[str, Any] | None:
        """从 LLM 回复解析分数。

        兼容：纯 JSON / markdown 代码块 / 前后带文字。
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
            score = parsed.get("score")
            if not isinstance(score, (int, float)):
                return None
            # 归一化到 0-10（防 LLM 输出 0-1 或 0-100）
            score = float(score)
            if score <= 1.0 and score > 0:
                score *= 10
            elif score > 10:
                score = score / 10
            return {
                "score": max(0.0, min(10.0, score)),
                "reason": parsed.get("reason", ""),
            }
        except (json.JSONDecodeError, TypeError):
            return None
