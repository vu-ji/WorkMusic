"""vector_store.py — Chroma 向量库封装

存储 chunk 的向量 + 元数据，提供 add / query / delete。
W6 用本地 Chroma（PersistentClient 落盘），W7 可换 Qdrant。

Chroma 概念对照（前端类比）：
- Collection ≈ 一张 MySQL 表（存同类型的数据）
- Document + Embedding + Metadata ≈ 一行记录（内容 + 向量 + 标签）
- Query ≈ SELECT ... ORDER BY 相似度 DESC LIMIT k

用法：
    store = VectorStore(path="./data", collection="catalog")
    store.add(docs=["文本1"], metadatas=[{"id": "M001"}])
    results = store.query("电子摇滚 BPM 140", top_k=3)

注意：Chroma 1.5.9 的 query() 返回 dict（不是带属性的对象），
且 ids/documents/metadatas/distances 都是双层嵌套（query_embeddings 是列表包列表）。
"""

from typing import Any

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection


class VectorStore:
    """Chroma 向量库封装。"""

    def __init__(self, path: str, collection_name: str = "catalog"):
        """初始化持久化向量库。

        Args:
            path: Chroma 数据目录（PersistentClient 落盘位置）
            collection_name: 集合名
        """
        self._client: ClientAPI = chromadb.PersistentClient(path=path)
        self._collection: Collection = self._client.get_or_create_collection(collection_name)

    def add(
        self,
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        ids: list[str] | None = None,
    ) -> None:
        """写入向量 + 原文 + 元数据。

        Args:
            embeddings: 每条文本的向量
            documents: 原始文本（检索后返回给 LLM 的内容）
            metadatas: 附加信息（如来源、页码）
            ids: 自定义 id（缺省由 Chroma 自动生成）
        """
        if ids is None:
            ids = [f"doc_{i}" for i in range(len(documents))]  # Chroma 1.5.9 强制要求 ids
        self._collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )

    def query(
        self,
        query_embedding: list[float],
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """按向量相似度检索。

        Args:
            query_embedding: 查询文本的向量
            top_k: 返回前 k 条

        Returns:
            [{"id", "document", "metadata", "distance"}]
            distance 越小越相似（Chroma 用 L2 距离）
        """
        result: dict = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

        # result 是 dict，且值为双层嵌套（外层对应 query_embeddings 列表）
        return [
            {
                "id": result["ids"][0][i],
                "document": result["documents"][0][i],
                "metadata": result["metadatas"][0][i],
                "distance": result["distances"][0][i],
            }
            for i in range(top_k)
        ]

    def count(self) -> int:
        """当前集合中的记录数。"""
        return self._collection.count()

    def delete_all(self) -> None:
        """清空集合（重建索引时用）。

        注意：Chroma 1.5.9 的 delete() 必须传 ids/where/where_document 至少一个。
        清空策略：先取全部 ids 再删。
        """
        all_ids = self._collection.get()["ids"]  # get() 返回 {"ids": [...], ...}
        if all_ids:
            self._collection.delete(ids=all_ids)
