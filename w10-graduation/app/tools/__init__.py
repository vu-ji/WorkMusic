"""app/tools/__init__.py — 工具注册层

毕业项目的工具集合：把 W4-W8 的能力注册成统一的工具接口。

工具接口约定：
    async def tool_name(arguments: dict) -> dict:
        return {"success": bool, "result": ..., "error": ...}

注册表结构：
    {工具名: {"schema": {"type": "object", "properties": {...}}, "handler": async fn}}
"""

import asyncio
import sys
from pathlib import Path
from typing import Any

# 路径补丁：复用 W4-W8 组件
_WORKMUSIC = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_WORKMUSIC / "w4-tool-use" / "src"))
sys.path.insert(0, str(_WORKMUSIC / "w6-rag" / "src"))
sys.path.insert(0, str(_WORKMUSIC / "w8-agent-arch" / "src"))

from tool_schema import search_catalog as w4_search_catalog  # noqa: E402


def _search_catalog_handler(arguments: dict[str, Any]) -> dict[str, Any]:
    """曲库检索（W4 逻辑，同步转异步包装）。"""
    try:
        result = w4_search_catalog(
            style=arguments.get("style", ""),
            bpm_min=arguments.get("bpm_min", 0),
            bpm_max=arguments.get("bpm_max", 200),
            budget=arguments.get("budget", 10**9),
        )
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


# RAG 知识检索（W6/W7 管线）——懒加载，首次调用时建索引
_rag_retriever = None
_RAG_DOCS = [
    "电子摇滚是融合电子音乐与摇滚风格的音乐类型，节奏强烈，适合运动场景",
    "BPM 130-150 属于中快速节奏，适合健身房有氧运动和力量训练",
    "古典钢琴曲节奏舒缓，适合睡前放松、冥想和专注工作",
    "重金属摇滚适合情绪宣泄场景，如压力释放和现场演出",
    "hip-hop 说唱节拍感强，适合街头运动、跑步和舞蹈训练",
    "RAG 检索系统通过 embedding 将文本向量化，用混合检索（BM25+向量）召回相关片段",
]


def _get_rag_retriever():
    """懒加载 RAG 检索器（首次调用建索引，后续复用）。"""
    global _rag_retriever
    if _rag_retriever is None:
        import tempfile
        from embedder import OllamaEmbedder
        from vector_store import VectorStore
        from retriever import HybridRetriever

        path = tempfile.mkdtemp()
        embedder = OllamaEmbedder()
        store = VectorStore(path=path, collection_name="graduation_rag")

        # 同步建索引：embed_batch 是 async，这里用 asyncio.run
        async def _build():
            embeds = await embedder.embed_batch(_RAG_DOCS)
            store.add(
                embeddings=embeds,
                documents=_RAG_DOCS,
                ids=[f"doc_{i}" for i in range(len(_RAG_DOCS))],
            )
            retriever = HybridRetriever(embedder, store)
            retriever.index_documents(_RAG_DOCS)
            return retriever

        _rag_retriever = asyncio.run(_build())
    return _rag_retriever


async def _knowledge_search_handler(arguments: dict[str, Any]) -> dict[str, Any]:
    """知识库检索（W6/W7 RAG 管线）。"""
    query = arguments.get("query", "")
    top_k = arguments.get("top_k", 2)
    if not query:
        return {"success": False, "error": "query 不能为空"}

    try:
        retriever = _get_rag_retriever()
        # 异步检索 + LLM 重排（复用 W7 Reranker）
        from reranker import LLMReranker

        results = await retriever.retrieve(query, top_k=top_k)
        reranker = LLMReranker(tier="middle")
        reranked = await reranker.rerank(query, results)
        return {
            "success": True,
            "result": [
                {
                    "content": r["document"],
                    "score": round(r.get("rerank_score", 0), 1),
                    "reason": r.get("rerank_reason", ""),
                }
                for r in reranked
            ],
        }
    except Exception as e:
        return {"success": False, "error": f"知识检索失败: {e}"}


def build_tools() -> dict[str, Any]:
    """构建毕业项目的全部工具。

    Returns:
        {工具名: {"schema": {...}, "handler": async fn}}
    """
    return {
        "search_catalog": {
            "schema": {
                "type": "object",
                "properties": {
                    "style": {"type": "string", "description": "音乐风格，如 电子摇滚"},
                    "bpm_min": {"type": "integer", "description": "最低 BPM"},
                    "bpm_max": {"type": "integer", "description": "最高 BPM"},
                    "budget": {"type": "integer", "description": "预算上限（元）"},
                },
                "required": ["style", "bpm_min", "bpm_max", "budget"],
            },
            "handler": _search_catalog_handler,
        },
        "knowledge_search": {
            "schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "要查询的问题"},
                    "top_k": {"type": "integer", "description": "返回条数，默认 2"},
                },
                "required": ["query"],
            },
            "handler": _knowledge_search_handler,
        },
    }
