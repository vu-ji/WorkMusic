"""tool_schema.py — 工具定义：JSON Schema + 实际函数

W4 核心概念：不给模型"编造"的选项——给它一个工具，它只能调工具获取数据。
JSON Schema 是 LLM 原生理解的格式，直接塞进 system prompt。

前端类比：Zod schema + API handler 绑定在一起。
Schema 告诉 LLM "传什么参数"，函数告诉系统 "收到后怎么执行"。
"""

from typing import Any


# ============================================================
# JSON Schema 定义
# ============================================================

def get_search_catalog_schema() -> dict[str, Any]:
    """返回 search_catalog 的 JSON Schema。

    LLM 看到这个 schema 后知道：要调 search_catalog，
    必须传 style / bpm_min / bpm_max / budget 四个参数。
    """
    return {
        "name": "search_catalog",
        "description": (
            "根据音乐风格、BPM 范围和预算检索曲库中的候选歌曲。"
            "返回匹配的歌曲列表，含歌曲名、命中理由、预估授权价和来源。"
            "如果曲库中无匹配数据，返回空列表。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "style": {
                    "type": "string",
                    "description": "音乐风格，如电子摇滚、流行、古典",
                },
                "bpm_min": {
                    "type": "integer",
                    "description": "最低 BPM",
                },
                "bpm_max": {
                    "type": "integer",
                    "description": "最高 BPM",
                },
                "budget": {
                    "type": "integer",
                    "description": "年度预算上限，单位元",
                },
            },
            "required": ["style", "bpm_min", "bpm_max", "budget"],
        },
    }


# ============================================================
# 实际函数（会被 tool_executor 调用）
# ============================================================

# Mock 曲库 — W4 阶段硬编码，W6 RAG 阶段接真实向量数据库
_MOCK_CATALOG: list[dict[str, Any]] = [
    {
        "m_id": "M001",
        "song_name": "甜蜜蜜",
        "style": "电子摇滚",
        "bpm": 140,
        "estimated_price": 2000,
        "hit_reason": "风格匹配，BPM 命中",
        "source": "Spotify",
    },
    {
        "m_id": "M002",
        "song_name": "花儿飞",
        "style": "电子摇滚",
        "bpm": 135,
        "estimated_price": 3500,
        "hit_reason": "BPM 命中，纯器乐",
        "source": "网易云音乐",
    },
    {
        "m_id": "M003",
        "song_name": "贝多芬",
        "style": "古典",
        "bpm": 100,
        "estimated_price": 5000,
        "hit_reason": "风格完全匹配",
        "source": "QQ 音乐",
    },
    {
        "m_id": "M004",
        "song_name": "双截棍",
        "style": "流行",
        "bpm": 128,
        "estimated_price": 1500,
        "hit_reason": "BPM 命中",
        "source": "Spotify",
    },
    {
        "m_id": "M005",
        "song_name": "大爆炸",
        "style": "电子摇滚",
        "bpm": 148,
        "estimated_price": 8000,
        "hit_reason": "风格匹配，高能 BPM",
        "source": "网易云音乐",
    },
]


def search_catalog(
    style: str, bpm_min: int, bpm_max: int, budget: int
) -> list[dict[str, Any]]:
    """检索曲库。按风格、BPM 范围、预算过滤。

    W4 阶段从 mock 数据过滤。W6 RAG 阶段接真实向量数据库。

    Returns:
        匹配的歌曲列表，预算超出的条目被剔除。返回空列表表示无匹配。
    """
    results = []
    for song in _MOCK_CATALOG:
        style_match = style.lower() == song["style"].lower()
        bpm_match = bpm_min <= song["bpm"] <= bpm_max
        budget_ok = song["estimated_price"] <= budget

        if style_match and bpm_match and budget_ok:
            results.append(song)

    return results


# ============================================================
# 工具注册表（静态字典——工具名 → {schema, function}）
# ============================================================

TOOLS: dict[str, dict[str, Any]] = {
    "search_catalog": {
        "schema": get_search_catalog_schema(),
        "fn": search_catalog,
    },
}
