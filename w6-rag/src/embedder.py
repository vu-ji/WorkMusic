"""embedder.py — Ollama embedding 封装

用本地 bge-m3 模型把文本转成向量。bge-m3 是阿里开源的 embedding 模型：
支持中文/英文/多语言，输出 1024 维向量。

为什么用 Ollama 而不是 sentence-transformers？
- local-first 架构：模型和数据都在本地，不出域
- 复用已有基础设施：跟 chat 一样走 /api/embed 接口
- 避免装 torch（几个 GB）——ollama 已内置推理

用法：
    embedder = OllamaEmbedder(model="bge-m3")
    vec = await embedder.embed_text("一首适合健身房的电子摇滚")
    vecs = await embedder.embed_batch(["文本1", "文本2"])

"""

import asyncio
import math
import httpx


class OllamaEmbedder:
    """Ollama embedding 封装。"""

    def __init__(self, model: str = "bge-m3", base_url: str = "http://localhost:11434"):
        """初始化。
        
        Args:
            model: Ollama 中的 embedding 模型名，默认 bge-m3
            base_url: Ollama 服务地址
        """
        self.model: str = model
        self.base_url: str = base_url
        self.http:httpx.AsyncClient = httpx.AsyncClient(base_url=base_url)    

    async def embed_text(self, text: str) -> list[float]:
        """单条文本 → 向量。

        Args:
            text: 输入文本

        Returns:
            1024 维浮点向量（bge-m3）
        """
        result: httpx.Response = await self.http.post(url="/api/embed", json={"model": self.model, "input": text})
        result.raise_for_status()
        return result.json()["embeddings"][0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量文本 → 向量列表。

        Ollama 的 /api/embed 支持一次传多条，
        embedding 任务适合批量——比逐个调用省 N 次 HTTP 往返。
        """
        result: httpx.Response = await self.http.post(url="/api/embed", json={"model": self.model, "input": texts})
        result.raise_for_status()
        return result.json()["embeddings"]

    def embed_text_sync(self, text: str) -> list[float]:
        """同步版本——测试或脚本里用 asyncio.run 不方便时调用。"""
        return asyncio.run(self.embed_text(text))


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """余弦相似度：两个向量的方向一致性 [-1, 1]。

    向量检索的评分基础。BGE-M3 输出 L2 归一化向量，
    余弦相似度 = 点积。

    Args:
        vec_a, vec_b: 等长浮点向量

    Returns:
        相似度（越大越相似）
    """
    # 公式：dot(a,b) / (|a| * |b|)
    if len(vec_a) != len(vec_b):
        raise ValueError(f"向量维度不一致: {len(vec_a)} vs {len(vec_b)}")
    dot = sum(x * y for x, y in zip(vec_a, vec_b))
    norm_a:float = math.sqrt(sum(x * x for x in vec_a))
    norm_b:float = math.sqrt(sum(y * y for y in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)