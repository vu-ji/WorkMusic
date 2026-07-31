"""reranker.py — 重排序（W7 补）

检索出的 top_k 候选里，向量和 BM25 都有噪声。
重排序 = 用更强的模型（cross-encoder / LLM）对候选逐条精排。

W6 只留接口，W7 实现：
- 方案 A：bge-reranker（Ollama 支持？）——cross-encoder，快但本地模型能力有限
- 方案 B：让 LLM 打分——慢但理解力强，适合候选少（3-5 条）的场景
"""

from typing import Any


class Reranker:
    """重排序器（接口占位）。"""

    async def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """对候选重排，返回带新分数的列表。

        Args:
            query: 原始查询
            candidates: retrieve() 返回的候选列表

        Returns:
            重排后的列表（含 rerank_score 字段）
        """
        # TODO (W7): 实现重排序
        return candidates
