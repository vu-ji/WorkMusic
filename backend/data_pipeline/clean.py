"""ChineseLyrics 数据清洗：去杂质、去重、规范化。

输入：data/raw/chinese-lyrics/lyrics{1..5}.json
输出：data/clean/lyrics_clean.jsonl（每行一条记录）

清洗规则：
1. 歌名：去掉《》包裹、去掉「原创…demo」等杂质后缀、strip 空白
2. 歌词：过滤非歌词行（段落标记/作曲/演唱/编曲/G调等）、strip、跳过空行
3. 去重：name+singer 归一化后去重（保留首条）
4. 剔除：歌名为空、歌词为空、纯无意义记录
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "chinese-lyrics"
CLEAN_FILE = Path(__file__).resolve().parents[1] / "data" / "clean" / "lyrics_clean.jsonl"

# 非歌词行：段落标记、制作信息、调式标记等
NON_LYRIC_PATTERNS = [
    r"^(主歌|副歌|前奏|间奏|尾奏|过渡|桥段|rap|Rap|RAP|说唱|唱)[0-9一二三四五六七八九十]*\s*[:：]?\s*$",
    r"^(作词|作曲|编曲|演唱|混音|录音|制作|监制|吉他|钢琴|和声|词|曲)[:：]?\s*\S*$",
    r"^[A-G](调|major|minor|大调|小调|sus|maj|min)?\s*$",
    r"^\d{1,2}[:：]\d{2}$",  # 时间戳
    r"^\s*[xX×*]\s*\d+\s*$",  # x2 / ×2 重复标记
    r"^([（(【\[].*[）)】\]]|——.*|----.*|…+.*)$",  # 括号注释/分隔线
]


def is_non_lyric(line: str) -> bool:
    """判断一行是否为非歌词内容。"""
    s = line.strip()
    if not s:
        return True
    for pat in NON_LYRIC_PATTERNS:
        if re.match(pat, s):
            return True
    return False


def clean_song_name(name: str) -> str:
    """歌名清洗：去《》、去 demo 等后缀。"""
    s = name.strip().replace("\xa0", " ")
    # 去掉「原创...demo」「...demo」「现场版」等杂质后缀（先于《》处理）
    s = re.sub(r"(原创)?[\w\s]*demo.*$", "", s, flags=re.IGNORECASE).strip()
    s = re.sub(r"(现场版|演唱会版|Live版|MV版|伴奏版|Remix|remix|重制版|Cover版).*$", "", s).strip()
    # 去《》包裹（非全匹配，兼容带后缀残留）
    s = re.sub(r"^《(.+)》", r"\1", s).strip()
    return s


def clean_lyric(lines: list[str]) -> list[str]:
    """歌词清洗：过滤非歌词行。"""
    return [ln.strip() for ln in lines if not is_non_lyric(ln)]


def normalize_key(name: str, singer: str) -> str:
    """归一化去重键：小写 + 去空白。"""
    return f"{name.strip().lower()}|{singer.strip().lower()}"


def process_all() -> tuple[int, int]:
    """处理全部 5 个文件，返回 (写入数, 去重丢弃数)。"""
    out = CLEAN_FILE
    out.parent.mkdir(parents=True, exist_ok=True)

    seen: set[str] = set()
    total_raw = 0
    dropped_dup = 0
    dropped_empty = 0
    written = 0

    with out.open("w", encoding="utf-8") as f:
        for i in range(1, 6):
            path = RAW_DIR / f"lyrics{i}.json"
            with path.open("r", encoding="utf-8") as jf:
                songs = json.load(jf)
            for item in songs:
                total_raw += 1
                name = clean_song_name(item.get("name", ""))
                singer = (item.get("singer") or "").strip()
                lyric = clean_lyric(item.get("lyric") or [])

                if not name or not singer or not lyric:
                    dropped_empty += 1
                    continue

                key = normalize_key(name, singer)
                if key in seen:
                    dropped_dup += 1
                    continue
                seen.add(key)

                rec = {
                    "name": name,
                    "singer": singer,
                    "lyric": "\n".join(lyric),
                    "lyric_lines": len(lyric),
                    "tag_source": "raw",
                }
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                written += 1

    return written, dropped_dup, dropped_empty, total_raw


if __name__ == "__main__":
    written, dup, empty, raw = process_all()
    print(f"原始 {raw} 条 → 写入 {written} 条")
    print(f"去重丢弃 {dup} 条, 空值丢弃 {empty} 条")
    assert written > 90_000, f"清洗后应 ≥ 9 万，实际 {written}"
