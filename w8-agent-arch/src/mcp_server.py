"""mcp_server.py — 把 search_catalog 暴露为 MCP 工具

W8 交付：接入 MCP server（项目硬性要求）。

把 W4 的 search_catalog（mock 曲库检索）注册成 MCP 工具，
用 `mcp run` 启动为 stdio 传输的 server。这样任何 MCP client
（Claude、Cursor、或我们自己的 Agent）都能通过标准协议调用它。

用法：
    启动 server：
        python mcp_server.py
        # 或 mcp run src/mcp_server.py

    测试（MCP Inspector / client）：
        tools/list  → 看到 search_catalog
        tools/call  → 传入 style/bpm_min/bpm_max/budget
"""

import sys
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer


server = MCPServer("music-catalog-server")


@server.tool(
    name="search_catalog",
    description="根据音乐风格、BPM 范围和预算检索曲库中的候选歌曲",
)
async def search_catalog(
    style: str,
    bpm_min: int,
    bpm_max: int,
    budget: int,
) -> list[dict[str, Any]]:
    """检索曲库。

    与 W4 的 mock 实现一致：按 style 精确匹配 + BPM 区间 + 预算过滤。

    Args:
        style: 音乐风格（如"电子摇滚"）
        bpm_min: 最低 BPM
        bpm_max: 最高 BPM
        budget: 年度预算上限（元）

    Returns:
        匹配的歌曲列表（空列表 = 无匹配）
    """
    catalog = _load_catalog()
    hits = []
    for song in catalog:
        if song["style"] != style:
            continue
        if not (bpm_min <= song["bpm"] <= bpm_max):
            continue
        if song["price"] > budget:
            continue
        hits.append(song)
    return hits


def _load_catalog() -> list[dict[str, Any]]:
    """加载 mock 曲库数据。"""
    # W4 的 mock 数据在 tool_schema.py 里，直接读 schema 中的示例（如有）
    # 这里为了独立可运行，内联一份最小 mock
    return [
        {"m_id": "M001", "song_name": "甜蜜蜜", "style": "电子摇滚", "bpm": 140, "price": 2000, "source": "Spotify"},
        {"m_id": "M002", "song_name": "Electric Sky", "style": "电子摇滚", "bpm": 150, "price": 3500, "source": "网易云音乐"},
        {"m_id": "M003", "song_name": "Neon Pulse", "style": "电子摇滚", "bpm": 135, "price": 2800, "source": "Spotify"},
        {"m_id": "M004", "song_name": "月光小夜曲", "style": "古典", "bpm": 70, "price": 1500, "source": "QQ音乐"},
        {"m_id": "M005", "song_name": "City Pop 夏夜", "style": "流行", "bpm": 110, "price": 1800, "source": "网易云音乐"},
    ]


if __name__ == "__main__":
    server.run()
