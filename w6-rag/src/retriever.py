"""retriever.py — 混合检索（向量 + BM25）

W6 核心交付。单一向量检索的问题：query 里的关键词可能没有匹配的 embedding 语义，
比如用户搜 "健身房 BGM" 而库里是 "fitness center background music"——向量能跨语言匹配，
但精确关键词（如歌名、版权方）向量反而弱。

混合检索 = 向量召回（语义）+ BM25 召回（关键词）→ 合并去重 → 按融合分排序。

前端类比：
- 向量检索 ≈ 全文模糊搜索（Elasticsearch match）
- BM25 ≈ 精确词频搜索（term query）
- 混合检索 ≈ 两者都跑一遍，结果用 RRF 融合
"""

import math
import re
from collections import Counter
from typing import Any
from embedder import OllamaEmbedder
from vector_store import VectorStore


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
        return re.findall(r"[\u4e00-\u9fff]|[a-zA-Z]+", text.lower())

    def index(self, docs: list[str]) -> None:
        """建立索引。"""
        self.docs = docs
        self.doc_token_counts = []
        self.doc_freq = Counter()

        for doc in docs:
            tokens: list[str] = self.tokenize(text=doc)
            counts = Counter(tokens)
            self.doc_token_counts.append(counts)
            # 每篇文档的"去重词集合"合并进 doc_freq
            # 注意：词在一篇文档里出现多次只计 1（df 是"多少篇文档含这个词"）
            self.doc_freq.update(counts.keys())
        
        total_words = sum(sum(c.values()) for c in self.doc_token_counts)
        self.avgdl = total_words / len(docs) if docs else 0.0

    def search(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """BM25 检索。

        Returns:
            [{"index": i, "score": float}]
        """
        if not self.docs:
            return []
        
        query_tokens:list[str] = self.tokenize(query)
        if not query_tokens:
            return []
        n: int = len(self.docs)
        scores: list[float] = []

        for i, counts in enumerate(self.doc_token_counts):
            doc_len = sum(counts.values())
            score = 0.0
            for token in query_tokens:
                tf = counts.get(token, 0)
                if tf == 0:
                    continue
                df = self.doc_freq[token]
                # IDF：词越稀有权重越高
                idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
                # 词频饱和 + 长度归一化
                denom = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
                score += idf * tf * (self.k1 + 1) / denom
            scores.append({"index": i, "score": score})

        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[:top_k]

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
        self.docs = docs  # 保存引用，retrieve 时补充 document 原文
        self.bm25.index(docs=docs)

    async def retrieve(
        self,
        query: str,
        top_k: int = 3,
        vector_weight: float = 0.5,
    ) -> list[dict[str, Any]]:
        """混合检索。"""
        # 1. 向量召回
        query_emb = await self.embedder.embed_text(query)
        vector_hits = self.store.query(query_emb, top_k)

        # 2. BM25 召回
        bm25_hits = self.bm25.search(query, top_k)

        # 3. RRF 融合（rank 从 1 开始）
        rrf_scores: dict[str, float] = {}
        for rank, hit in enumerate(vector_hits, start=1):
            doc_id = hit["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (self.rrf_k + rank)
        for rank, hit in enumerate(bm25_hits, start=1):
            doc_id = f"doc_{hit['index']}"   # BM25 的 index → store 里的 doc_{i}
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (self.rrf_k + rank)

        # 4. 按融合分排序取 top_k
        ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        # 5. 补充 document/metadata（从向量命中和 self.docs 里拿）
        results = []
        vector_by_id = {h["id"]: h for h in vector_hits}
        for doc_id, score in ranked:
            idx = int(doc_id.split("_")[1])
            results.append({
                "id": doc_id,
                "document": self.docs[idx],
                "metadata": vector_by_id.get(doc_id, {}).get("metadata"),
                "score": score,
            })
        return results

