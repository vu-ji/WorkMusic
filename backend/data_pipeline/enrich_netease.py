"""网易云音乐真实热度回填：popularity（0-100 真实值）。

中文歌名/歌手匹配（iTunes 因中英名不匹配弃用）。策略：
搜索「歌手 歌名」→ 结果中 artists 名称归一化后与 singer 完全匹配的项
→ 取 popularity 最高者回填。不匹配则跳过（不影响 LLM 标注）。

用法：
    python enrich_netease.py --limit 200    # 子集验证匹配率
    python enrich_netease.py --full         # 全量（约 10 万次请求，注意限速）
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import time
import urllib.parse
import urllib.request
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "workmusic.db"
SEARCH_URL = "https://music.163.com/api/search/get/web?s={q}&type=1&limit=5"
DETAIL_URL = "https://music.163.com/api/song/detail?ids=[{sid}]"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://music.163.com/",
    "Cookie": "appver=2.0.2",
}
REQUEST_INTERVAL = 2.0  # 秒/请求，网易云搜索接口风控严格（实测 0.8s×100 次触发 code 405）


def http_get(url: str) -> dict:
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            if attempt == 2:
                return {}
            time.sleep(1.5 * (attempt + 1))
    return {}


def normalize(s: str) -> str:
    s = re.sub(r"[（(【\[].*?[）)】\]]", "", s or "")
    return re.sub(r"[\s\-_.·]+", "", s).lower()


def fetch_popularity(singer: str, name: str) -> float | None:
    """搜索并精确匹配歌手，返回最高 popularity。遇风控（405/460/462）退避重试。"""
    for attempt in range(3):
        songs = http_get(SEARCH_URL.format(q=urllib.parse.quote(f"{singer} {name}")))
        code = songs.get("code")
        if code in (405, 460, -460, -462):
            wait = 45 * (attempt + 1)
            print(f"    风控 code={code}, 等待 {wait}s", flush=True)
            time.sleep(wait)
            continue
        results = songs.get("result", {}).get("songs", [])
        nsinger = normalize(singer)
        best: float | None = None
        for s in results:
            artists = [a.get("name", "") for a in s.get("artists", [])]
            if any(normalize(a) == nsinger for a in artists):
                try:
                    pop = float(s.get("popularity") or 0)
                except (TypeError, ValueError):
                    pop = 0.0
                if pop > 0 and (best is None or pop > best):
                    best = pop
        return best
    return None


def enrich_batch(conn: sqlite3.Connection, limit: int | None) -> tuple[int, int]:
    sql = "SELECT id, name, singer FROM songs WHERE popularity IS NULL"
    params: tuple = ()
    if limit:
        sql += " LIMIT ?"
        params = (limit,)
    rows = conn.execute(sql, params).fetchall()

    hit = 0
    for i, (sid, name, singer) in enumerate(rows):
        pop = fetch_popularity(singer, name)
        if pop is not None:
            conn.execute(
                "UPDATE songs SET popularity=?, updated_at=? WHERE id=?",
                (pop, time.strftime("%Y-%m-%d"), sid),
            )
            hit += 1
        if (i + 1) % 20 == 0:
            conn.commit()
            print(f"  [{i+1}/{len(rows)}] 命中 {hit}", flush=True)
        time.sleep(REQUEST_INTERVAL)

    conn.commit()
    return len(rows), hit


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--full", action="store_true")
    args = ap.parse_args()

    conn = sqlite3.connect(DB_PATH)
    limit = None if args.full else args.limit
    tried, hit = enrich_batch(conn, limit)
    rate = hit / tried * 100 if tried else 0
    print(f"\n尝试 {tried} 首, 命中 {hit} 首, 匹配率 {rate:.1f}%")
    conn.close()
