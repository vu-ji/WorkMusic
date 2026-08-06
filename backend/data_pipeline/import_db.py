"""导入清洗后的数据到 SQLite。

数据库：data/workmusic.db
表：songs（真实字段 + 元数据回填预留位）

bpm / genre / tags / popularity 等元数据列初值为 NULL，由 enrich_*.py 脚本
基于真实数据源回填（tag_source 记录来源，不产生合成字段）。
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "workmusic.db"
CLEAN_FILE = Path(__file__).resolve().parents[1] / "data" / "clean" / "lyrics_clean.jsonl"

SCHEMA = """
CREATE TABLE IF NOT EXISTS songs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    singer       TEXT NOT NULL,
    lyric        TEXT NOT NULL,
    lyric_lines  INTEGER NOT NULL DEFAULT 0,
    release_year INTEGER,            -- 真实回填（如 iTunes）
    language     TEXT,               -- 真实回填
    genre        TEXT,               -- 真实回填（iTunes genre）
    bpm          INTEGER,            -- 真实回填（可能为 NULL）
    mood_tags    TEXT,               -- JSON 数组，真实/标注回填
    scene_tags   TEXT,               -- JSON 数组
    popularity   REAL,               -- 真实热度（如网易云 popularity）
    tag_source   TEXT NOT NULL DEFAULT 'raw',  -- raw|itunes|netease|llm
    updated_at   TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_songs_name_singer ON songs(name, singer);
CREATE INDEX IF NOT EXISTS idx_songs_singer ON songs(singer);
CREATE INDEX IF NOT EXISTS idx_songs_genre ON songs(genre);
CREATE INDEX IF NOT EXISTS idx_songs_bpm ON songs(bpm);
"""


def init_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    return conn


def import_clean(conn: sqlite3.Connection) -> int:
    """全量导入清洗后的 jsonl，返回写入数。"""
    rows = []
    with CLEAN_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            rows.append((rec["name"], rec["singer"], rec["lyric"], rec["lyric_lines"]))
    conn.executemany(
        "INSERT OR IGNORE INTO songs(name, singer, lyric, lyric_lines, tag_source) "
        "VALUES(?, ?, ?, ?, 'raw')",
        rows,
    )
    conn.commit()
    return len(rows)


if __name__ == "__main__":
    conn = init_db()
    n = import_clean(conn)
    count = conn.execute("SELECT COUNT(*) FROM songs").fetchone()[0]
    print(f"导入候选 {n} 条, 库内实际 {count} 条")
    # 抽样看数据
    for row in conn.execute("SELECT name, singer, lyric_lines, tag_source FROM songs LIMIT 3"):
        print("  样本:", row)
    conn.close()
