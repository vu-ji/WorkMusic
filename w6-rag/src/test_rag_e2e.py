"""W7 e2e：完整 RAG 管线验证 —— 检索 → 重排 → 对比

对比重排前后 top1 是否改善，量化 rerank 的价值。
需要 ollama 运行中。用法：python src/test_rag_e2e.py
"""

import asyncio
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from embedder import OllamaEmbedder
from vector_store import VectorStore
from retriever import HybridRetriever
from reranker import LLMReranker


DOCS = [
    "一首适合健身房的电子摇滚 BPM 140 动感节奏强烈",
    "古典钢琴曲 安静优雅 适合睡前放松聆听",
    "流行歌 旋律优美 适合逛街购物时听",
    "重金属摇滚 现场演出 嘶吼唱腔 情绪宣泄",
    "轻音乐 自然白噪音 适合冥想和工作专注",
    "hip-hop 说唱 节拍感强 适合街头运动和跑步",
]


async def main():
    print("=" * 60)
    print("W7 完整 RAG 管线 e2e：检索 → 重排")
    print("=" * 60)

    embedder = OllamaEmbedder()
    store = VectorStore(path=tempfile.mkdtemp(), collection_name="e2e")
    retriever = HybridRetriever(embedder, store)
    reranker = LLMReranker(tier="light")

    # 1. 入库
    embeds = await embedder.embed_batch(DOCS)
    store.add(
        embeddings=embeds,
        documents=DOCS,
        ids=[f"doc_{i}" for i in range(len(DOCS))],
    )
    retriever.index_documents(DOCS)
    print(f"入库 {len(DOCS)} 条\n")

    # 2. 三个 query：分别测试重排是否改善
    queries = [
        "给健身房找动感的电子摇滚",
        "适合睡前听的安静音乐",
        "跑步时听的快节奏说唱",
    ]

    for q in queries:
        print(f"--- 查询: {q} ---")
        # 检索（不重排）
        retrieved = await retriever.retrieve(q, top_k=3)
        print("  检索 top3:")
        for c in retrieved:
            print(f"    {c['id']} | RRF分:{c['score']:.4f} | {c['document'][:24]}")

        # 重排
        reranked = await reranker.rerank(q, retrieved)
        print("  重排后:")
        for c in reranked:
            print(f"    {c['id']} | LLM分:{c['rerank_score']} | {c['document'][:24]}")

        # 对比 top1
        before = retrieved[0]["id"]
        after = reranked[0]["id"]
        changed = "✓ 改善" if before != after else "= 不变"
        print(f"  top1: {before} → {after} {changed}\n")

    print("=" * 60)
    print("W7 e2e 完成")


if __name__ == "__main__":
    asyncio.run(main())
