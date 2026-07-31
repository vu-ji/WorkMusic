"""W6 pytest 测试 —— 切分 + embedding + 向量库 + 混合检索"""

# TODO: from chunker import chunk_by_fixed_size, chunk_by_paragraph, chunk_by_sentences
# TODO: from embedder import OllamaEmbedder, cosine_similarity
# TODO: from vector_store import VectorStore
# TODO: from retriever import BM25, HybridRetriever


class TestChunker:
    """切分策略测试"""

    def test_fixed_size_basic(self):
        """100 字文本，chunk_size=50 → 2 块"""
        pass

    def test_fixed_size_with_overlap(self):
        """100 字文本，chunk_size=50, overlap=10 → 重叠生效"""
        pass

    def test_fixed_size_empty(self):
        """空文本 → 返回 []"""
        pass

    def test_paragraph_basic(self):
        """按空行切段"""
        pass

    def test_paragraph_small_chunk_merged(self):
        """短段合并到前一段"""
        pass

    def test_sentence_basic(self):
        """按中文标点断句"""
        pass

    def test_sentence_long_chunk(self):
        """无标点长文本 → 硬切"""
        pass


class TestCosineSimilarity:
    """余弦相似度测试"""

    def test_same_vector(self):
        """相同向量 → 相似度 1"""
        pass

    def test_orthogonal_vectors(self):
        """垂直向量 → 相似度 0"""
        pass

    def test_opposite_vectors(self):
        """相反向量 → 相似度 -1"""
        pass


class TestBM25:
    """BM25 检索测试"""

    def test_keyword_match(self):
        """查询词在文档中 → 排前面"""
        pass

    def test_rare_term_higher_score(self):
        """稀有词比常见词权重高"""
        pass

    def test_empty_query(self):
        """空查询 → 返回空"""
        pass


class TestHybridRetriever:
    """混合检索测试（需要 Ollama bge-m3 运行中）"""

    @pytest.mark.asyncio
    async def test_retrieve_returns_results(self):
        """索引 3 段文档后查询 → 返回 top_k"""
        pass
