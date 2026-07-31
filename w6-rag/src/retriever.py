"""retriever.py — 混合检索（向量 + BM25）

W6 核心交付。单一向量检索的问题：query 里的关键词可能没有匹配的 embedding 语义，
比如用户搜 "健身房 BGM" 而库里是 "fitness center background music"——向量能跨语言匹配，
但精确关键词（如歌名、版权方）向量反而弱。

混合检索 = 向量召回（语义）+ BM25 召回（关键词）→ 合并去重 → 按融合分排序。

前端类比：
- 向量检索 ≈ 全文模糊搜索（Elasticsearch match）
- BM25 ≈ 精确词频搜索（term query）
- 混合检索 ≈ 两者都跑一遍，结果用 RRF 融合

TODO: 完成下面的 TODO 标记项。
"""

import math
import re
from collections import Counter
from typing import Any

# TODO: from embedder import OllamaEmbedder
# TODO: from vector_store import VectorStore


class BM25:
    """轻量 BM25 实现（不依赖外部库）。

    BM25 核心思想：词频越高越相关，但被太多文档包含的词（停用词）权重降低。
    公式：
        score(q, d) = Σ IDF(t) * tf(t,d) * (k1+1) / (tf(t,d) + k1 * (1 - b + b * |d|/avgdl))
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        """初始化。

        Args:
            k1: 词频饱和参数（越大词频影响越大）
            b: 文档长度归一化（越大长文档惩罚越强）
        """
        self.k1 = k1
        self.b = b
        self.docs: list[str] = []
        self.doc_token_counts: list[Counter] = []
        self.doc_freq: Counter = Counter()  # 每个词出现在几篇文档
        self.avgdl: float = 0.0

    def tokenize(self, text: str) -> list[str]:
        """分词：中文按字符、英文按单词。"""
        # TODO: 中文提取（保留中文+英文单词）
        # 简单方案：re.findall(r"[\u4e00-\u9fff]|[a-zA-Z]+", text.lower())
        pass

    def index(self, docs: list[str]) -> None:
        """建立索引。"""
        # TODO: 对每篇 doc：分词 → 记录词频 → 统计 doc_freq
        pass

    def search(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """BM25 检索。

        Returns:
            [{"index": i, "score": float}]
        """
        # TODO: 对每篇 doc 计算 BM25 分数，取 top_k
        pass


class HybridRetriever:
    """混合检索器：向量召回 + BM25 召回 → RRF 融合。"""

    def __init__(
        self,
        embedder,
        store: "VectorStore",
        rrf_k: int = 60,
    ) -> None:
        """初始化。

        Args:
            embedder: OllamaEmbedder 实例
            store: VectorStore 实例
            rrf_k: RRF 融合常数（默认 60，影响排名靠后的文档）
        """
        self.embedder = embedder
        self.store = store
        self.rrf_k = rrf_k
        self.bm25 = BM25()

    def index_documents(self, docs: list[str]) -> None:
        """对全部文档建 BM25 索引（向量索引在 store.add 时建）。"""
        # TODO: self.bm25.index(docs)
        pass

    async def retrieve(
        self,
        query: str,
        top_k: int = 3,
        vector_weight: float = 0.5,
    ) -> list[dict[str, Any]]:
        """混合检索。

        Args:
            query: 查询文本
            top_k: 最终返回条数
            vector_weight: 向量召回占比（1 - vector_weight 给 BM25）

        Returns:
            [{"id", "document", "metadata", "score"}]
        """
        # TODO:
        # 1. query_emb = await self.embedder.embed_text(query)
        # 2. vector_hits = self.store.query(query_emb, top_k)
        # 3. bm25_hits = self.bm25.search(query, top_k)
        # 4. RRF 融合：score = Σ 1/(rank + rrf_k)
        # 5. 取融合分 top_k
        pass
