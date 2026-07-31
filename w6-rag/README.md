# W6 · RAG

个人知识库问答系统——把 W4 的 mock 曲库换成真实向量检索。

## 目录

```
src/
├── chunker.py       # 切分策略（fixed/paragraph/sentence）
├── embedder.py      # Ollama bge-m3 embedding
├── vector_store.py  # Chroma 向量库（PersistentClient 落盘）
├── retriever.py     # 混合检索（向量 + BM25 + RRF 融合）
├── reranker.py      # 重排序（W7 补）
└── test_rag.py      # pytest 测试
```

## 依赖

```bash
uv pip install chromadb        # 已装
ollama pull bge-m3             # 本地已有（1.2GB embedding 模型）
```

## 跑

```bash
make test
```

## 管线

```
文档 → chunker 切分 → embedder 向量化 → vector_store 入库
查询 → embedder 向量化 → retriever 混合检索（向量+BM25+RRF）→ reranker 重排 → LLM 回答
```

## 与 W4 的衔接

W4 的 `search_catalog` 是硬编码 mock 曲库。W6 把 mock 换成真实检索：
- W4 只能按 style/bpm/budget 精确过滤
- W6 支持语义检索（"节奏感强适合健身房的歌" → 向量匹配）
