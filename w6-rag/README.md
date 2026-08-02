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
└── test_rag.py      # pytest 15 条测试
```

## 依赖

```bash
uv pip install chromadb        # 已装（1.5.9）
ollama pull bge-m3             # 本地已有（1.2GB embedding 模型）
```

## 跑

```bash
make test          # 20 条全绿（含真实 bge-m3 混合检索 + LLM 重排）
python src/test_rag_e2e.py   # 完整管线 e2e（检索→重排对比，需 ollama）
```

## 管线

```
文档 → chunker 切分 → embedder 向量化 → vector_store 入库
查询 → embedder 向量化 → retriever 混合检索（向量+BM25+RRF）→ reranker 重排 → LLM 回答
```

## 实测数据

| 指标 | 结果 |
|---|---|
| bge-m3 向量维度 | 1024 |
| 语义相似度 | 同类 0.606 vs 跨类 0.438（排序正确）|
| BM25 稀有词 | IDF 生效，健身房 排第一 |
| RRF 融合 | 双命中（向量+BM25）压过单边词频极高命中 |
| LLM 重排 | 7b 打分可解释（"符合动感电子摇滚需求"），噪声候选压到 0-2 分 |
| 重排稳定性 | 3 个 query top1 全部稳定（检索质量高时重排不改判，只拉开分数）|

## Chroma 1.5.9 踩坑（已修）

1. `query()` 返回 **dict** 不是对象——`result["ids"]` 不是 `result.ids`，且值是双层嵌套
2. `add()` 强制要求 `ids`——`ids=None` 直接 TypeError
3. `delete()` 强制要求条件——空调用 ValueError，清空需先 get 全部 ids

## 与 W4 的衔接

W4 的 `search_catalog` 是硬编码 mock 曲库。W6 把 mock 换成真实检索：
- W4 只能按 style/bpm/budget 精确过滤
- W6 支持语义检索（"节奏感强适合健身房的歌" → 向量匹配）
