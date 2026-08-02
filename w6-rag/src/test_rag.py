"""W6 pytest 测试 —— 切分 + embedding + 向量库 + 混合检索"""

import asyncio
import tempfile

import pytest
from chunker import chunk_by_fixed_size, chunk_by_paragraph, chunk_by_sentences
from embedder import OllamaEmbedder, cosine_similarity
from vector_store import VectorStore
from retriever import BM25, HybridRetriever


class TestChunker:
    """切分策略测试"""

    def test_fixed_size_basic(self):
        """100 字文本，chunk_size=50 → 2 块"""
        text = "A" * 100
        chunks = chunk_by_fixed_size(text, chunk_size=50, overlap=0)
        assert len(chunks) == 2
        assert chunks[0] == "A" * 50
        assert chunks[1] == "A" * 50

    def test_fixed_size_with_overlap(self):
        """100 字文本，chunk_size=50, overlap=10 → 重叠生效"""
        # 步进 = 50-10 = 40 → 块: [0:50], [40:90], [80:100]
        chunks = chunk_by_fixed_size("0123456789" * 10, chunk_size=50, overlap=10)
        assert len(chunks) == 3
        assert chunks[0][-10:] == chunks[1][:10]  # 相邻块尾部=下一块头部

    def test_fixed_size_empty(self):
        """空文本 → 返回 []"""
        assert chunk_by_fixed_size("") == []

    def test_paragraph_basic(self):
        """按空行切段"""
        text = "段一内容\n\n段二内容\n\n段三内容"
        chunks = chunk_by_paragraph(text, min_chunk_size=2)
        assert len(chunks) == 3

    def test_paragraph_small_chunk_merged(self):
        """短段合并到前一段"""
        text = "短段\n\n" + "B" * 200
        chunks = chunk_by_paragraph(text, min_chunk_size=100)
        assert len(chunks) == 1
        assert "短段" in chunks[0]

    def test_sentence_basic(self):
        """按中文标点断句"""
        # 文本超 max → 触发断句逻辑
        text = "第一句内容较长。" * 10 + "第二句内容较长！" * 10 + "第三句内容较长？" * 10
        chunks = chunk_by_sentences(text, max_chunk_size=60)
        assert len(chunks) >= 3  # 至少按 3 个句号断

    def test_sentence_long_chunk(self):
        """无标点长文本 → 硬切"""
        text = "X" * 1200
        chunks = chunk_by_sentences(text, max_chunk_size=500)
        assert len(chunks) >= 2
        assert all(len(c) <= 500 + 200 for c in chunks)  # 允许 overlap


class TestCosineSimilarity:
    """余弦相似度测试"""

    def test_same_vector(self):
        """相同向量 → 相似度 1"""
        assert abs(cosine_similarity([1, 2, 3], [1, 2, 3]) - 1.0) < 1e-9

    def test_orthogonal_vectors(self):
        """垂直向量 → 相似度 0"""
        assert abs(cosine_similarity([1, 0], [0, 1])) < 1e-9

    def test_opposite_vectors(self):
        """相反向量 → 相似度 -1"""
        assert abs(cosine_similarity([1, 2], [-1, -2]) + 1.0) < 1e-9


class TestBM25:
    """BM25 检索测试"""

    def test_keyword_match(self):
        """查询词在文档中 → 排前面"""
        bm = BM25()
        bm.index(["电子摇滚 BPM 140 适合健身房", "古典钢琴曲 安静 优雅", "电子摇滚 现场 演唱会"])
        r = bm.search("电子摇滚", top_k=2)
        # 两篇含"电子摇滚"，第一篇更短 → 长度归一化后得分更高
        assert r[0]["index"] in (0, 2)
        assert r[0]["score"] > 0

    def test_rare_term_higher_score(self):
        """稀有词比常见词权重高"""
        bm = BM25()
        # "电子"出现在全部文档，但"健身房"只在第 1 篇
        bm.index(["电子 健身房", "电子 电子 电子", "电子 电子"])
        r = bm.search("电子 健身房", top_k=1)
        assert r[0]["index"] == 0  # 稀有词"健身房"带来更高权重

    def test_empty_query(self):
        """空查询 → 返回空"""
        bm = BM25()
        bm.index(["内容一", "内容二"])
        assert bm.search("") == []


class TestHybridRetriever:
    """混合检索测试（需要 Ollama bge-m3 运行中）"""

    @pytest.mark.asyncio
    async def test_retrieve_returns_results(self):
        """索引 3 段文档后查询 → 返回 top_k"""
        docs = [
            "一首适合健身房的电子摇滚 BPM 140",
            "古典钢琴曲 安静优雅 适合睡前",
            "电子摇滚 现场 演唱会 节奏强烈",
        ]
        path = tempfile.mkdtemp()

        embedder = OllamaEmbedder()
        store = VectorStore(path=path, collection_name="test_hybrid")

        # 向量入库（ids 用 doc_0/doc_1/doc_2 对齐 BM25 index）
        embeds = await embedder.embed_batch(docs)
        store.add(embeddings=embeds, documents=docs, ids=[f"doc_{i}" for i in range(len(docs))])

        # BM25 索引
        retriever = HybridRetriever(embedder, store)
        retriever.index_documents(docs)

        results = await retriever.retrieve("健身房电子摇滚", top_k=2)
        assert len(results) == 2
        assert results[0]["id"] == "doc_0"  # 向量+BM25 双命中，RRF 融合分最高
        assert "document" in results[0]
        assert "score" in results[0]
        assert results[0]["score"] > results[1]["score"]

    @pytest.mark.asyncio
    async def test_rrf_fusion_promotes_dual_hit(self):
        """双命中（向量+BM25）融合分高于单边命中"""
        # 构造 3 篇：doc_0 同时命中语义和关键词，doc_1 只命中关键词
        docs = [
            "健身房 电子摇滚 BPM 140 动感节奏",
            "电子摇滚 电子摇滚 电子摇滚 电子摇滚 电子摇滚 电子摇滚",  # 词频极高但语义弱
            "安静 古典 钢琴 睡前 轻音乐",
        ]
        path = tempfile.mkdtemp()
        embedder = OllamaEmbedder()
        store = VectorStore(path=path, collection_name="test_rrf")
        embeds = await embedder.embed_batch(docs)
        store.add(embeddings=embeds, documents=docs, ids=[f"doc_{i}" for i in range(len(docs))])

        retriever = HybridRetriever(embedder, store)
        retriever.index_documents(docs)

        results = await retriever.retrieve("适合健身房的电子摇滚", top_k=3)
        # doc_0 在向量和 BM25 都出现 → RRF 融合分应最高
        assert results[0]["id"] == "doc_0"


class TestLLMReranker:
    """LLM 重排序测试（需要 ollama 运行中）"""

    def test_parse_score_plain_json(self):
        """纯 JSON 解析"""
        from reranker import LLMReranker
        r = LLMReranker()
        assert r._parse_score('{"score": 8, "reason": "匹配"}') == {"score": 8.0, "reason": "匹配"}

    def test_parse_score_markdown(self):
        """markdown 代码块解析"""
        from reranker import LLMReranker
        r = LLMReranker()
        parsed = r._parse_score('```json\n{"score": 7, "reason": "ok"}\n```')
        assert parsed["score"] == 7.0

    def test_parse_score_normalization(self):
        """分数归一化：0-1 → 0-10，>10 → /10"""
        from reranker import LLMReranker
        r = LLMReranker()
        assert r._parse_score('{"score": 0.6}')["score"] == 6.0
        assert r._parse_score('{"score": 85}')["score"] == 8.5

    def test_parse_score_invalid(self):
        """非法格式 → None"""
        from reranker import LLMReranker
        r = LLMReranker()
        assert r._parse_score("不是 JSON") is None
        assert r._parse_score('{"score": "abc"}') is None

    @pytest.mark.asyncio
    async def test_rerank_reorders_candidates(self):
        """候选被 LLM 重排：不匹配的排在后面"""
        from reranker import LLMReranker
        reranker = LLMReranker(tier="light")
        candidates = [
            {"id": "doc_0", "document": "一首适合健身房的电子摇滚 BPM 140 动感节奏", "metadata": None, "score": 0.5},
            {"id": "doc_1", "document": "古典钢琴曲 安静优雅 适合睡前听", "metadata": None, "score": 0.4},
            {"id": "doc_2", "document": "流行歌 旋律优美 适合逛街", "metadata": None, "score": 0.3},
        ]
        results = await reranker.rerank("给健身房找动感的电子摇滚", candidates)
        assert len(results) == 3
        assert results[0]["id"] == "doc_0"  # 最匹配的排第一
        assert "rerank_score" in results[0]
        assert "rerank_reason" in results[0]
        assert results[0]["rerank_score"] >= results[1]["rerank_score"]
