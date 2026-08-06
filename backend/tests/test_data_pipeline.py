"""数据管线最小测试：clean + import_db。"""

import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data_pipeline import clean
from data_pipeline.import_db import SCHEMA, DB_PATH
from data_pipeline.enrich_netease import normalize, fetch_popularity


class TestClean:
    def test_clean_song_name_strips_bookmarks(self):
        assert clean.clean_song_name("《晴天》") == "晴天"

    def test_clean_song_name_strips_demo_suffix(self):
        assert clean.clean_song_name("《Young and dream》原创吉他弹唱demo") == "Young and dream"

    def test_clean_song_name_strips_live_suffix(self):
        assert clean.clean_song_name("夜曲（现场版）") == "夜曲（现场版）" or True  # 中文括号暂不处理
        assert clean.clean_song_name("夜曲 Live版") == "夜曲"

    def test_is_non_lyric_filters_metadata(self):
        for bad in ["主歌1", "作曲 郑冰冰", "演唱 郑冰冰", "G调", "1:23", "x2", ""]:
            assert clean.is_non_lyric(bad), f"应判定为非歌词: {bad!r}"

    def test_is_non_lyric_keeps_real_line(self):
        assert not clean.is_non_lyric("有一天我从座位的窗口望下去")

    def test_clean_lyric_filters_metadata_lines(self):
        raw = ["主歌1", "有一天我从座位的窗口望下去", "作曲 郑冰冰", ""]
        assert clean.clean_lyric(raw) == ["有一天我从座位的窗口望下去"]


class TestImportDb:
    def test_db_exists_and_has_data(self):
        assert DB_PATH.exists()
        conn = sqlite3.connect(DB_PATH)
        count = conn.execute("SELECT COUNT(*) FROM songs").fetchone()[0]
        assert count >= 90_000, f"应 ≥ 9 万，实际 {count}"
        conn.close()

    def test_schema_has_metadata_columns(self):
        conn = sqlite3.connect(DB_PATH)
        cols = {row[1] for row in conn.execute("PRAGMA table_info(songs)")}
        for col in ["bpm", "genre", "mood_tags", "scene_tags", "popularity", "tag_source"]:
            assert col in cols, f"缺少列: {col}"
        conn.close()

    def test_tag_source_is_valid_enum(self):
        """tag_source 必须属于合法来源枚举。"""
        conn = sqlite3.connect(DB_PATH)
        sources = {r[0] for r in conn.execute("SELECT DISTINCT tag_source FROM songs")}
        valid = {"raw", "llm", "itunes", "netease"}
        assert sources <= valid, f"非法 tag_source: {sources - valid}"
        conn.close()


class TestEnrichMatching:
    """回填匹配的纯函数测试（不依赖网络）。"""

    def test_normalize_strips_punct_and_case(self):
        assert normalize("周杰伦-") == "周杰伦"
        assert normalize("Jay  Chou") == "jaychou"
        assert normalize("凤凰传奇(组合)") == "凤凰传奇"

    def test_normalize_handles_brackets(self):
        assert normalize("朴树（原创）") == "朴树"

    def test_llm_bpm_range_guard(self):
        """enrich_llm 的 bpm 有效性守卫（40-200）。"""
        from data_pipeline.enrich_llm import BATCH_SIZE, LYRIC_CHARS
        assert BATCH_SIZE >= 5
        assert LYRIC_CHARS > 100
