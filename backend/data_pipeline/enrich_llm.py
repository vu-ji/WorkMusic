"""LLM 标注回填：基于歌词内容推断 mood / scene / genre / bpm。

真实歌词内容 → DeepSeek 推断（tag_source=llm），非合成字段。
bpm 为风格/节奏推断估计值（真实音频 BPM 在免费公开 API 上对中文歌不可得，
见 enrich_itunes.py 注释与项目 notes）。

用法：
    python enrich_llm.py --limit 20        # 子集验证输出质量 + 成本
    python enrich_llm.py --limit 2000      # 批量标注
    python enrich_llm.py --full            # 全量（约 10 万首，注意成本与时长）

API key 来源：环境变量 LLM_API_KEY，或 ~/.pi/agent/auth.json（Pi 已配置的 DeepSeek key）。
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "workmusic.db"
PI_AUTH = Path.home() / ".pi" / "agent" / "auth.json"

API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"
BATCH_SIZE = 10         # 每批歌曲数（模型输出数组，批内顺序对应）
LYRIC_CHARS = 400       # 每首歌词截断长度

SYSTEM_PROMPT = """你是音乐标签标注器。根据给定的中文歌词内容（可能有杂质），推断每首歌曲的元数据标签。
输出严格 JSON 数组，数组元素顺序与输入歌曲顺序一一对应。每个元素格式：
{"mood_tags": ["标签1","标签2"], "scene_tags": ["场景1"], "genre": "流派", "bpm": 整数}
规则：
- mood_tags：2-3 个情绪标签（如 治愈/热血/伤感/欢快/思念/励志/孤独/浪漫），从歌词语义推断
- scene_tags：1-2 个适用场景（如 健身/通勤/深夜/派对/学习/旅行/婚礼/开车），从歌词主题推断
- genre：单一中文流派（如 流行/摇滚/民谣/说唱/古风/电子/儿歌/纯音乐），从歌词风格判断；不确定用"流行"
- bpm：根据歌词节奏感和风格估计 60-180 的整数（如 说唱/舞曲偏快 110-140，民谣/抒情偏慢 60-90）；无法判断给 0
- 全部用中文，bpm 必须是整数或 0"""

USER_TEMPLATE = "歌曲：{name} - {singer}\n歌词片段：\n{lyric}"


def get_api_key() -> str:
    key = os.environ.get("LLM_API_KEY")
    if key:
        return key
    if PI_AUTH.exists():
        try:
            data = json.loads(PI_AUTH.read_text())
            return data.get("deepseek", {}).get("key", "")
        except Exception:
            pass
    raise SystemExit("未找到 LLM API key：设置环境变量 LLM_API_KEY，或确认 ~/.pi/agent/auth.json 存在")


def lyric_snippet(lyric: str) -> str:
    """取歌词中段（副歌区）片段。"""
    lines = lyric.split("\n")
    if len(lines) <= 12:
        return lyric[:LYRIC_CHARS]
    mid = len(lines) // 2
    return "\n".join(lines[mid - 4 : mid + 4])[:LYRIC_CHARS]


def call_llm(key: str, items: list[dict]) -> list[dict]:
    """调用 DeepSeek，返回每首的标签 dict。"""
    user_content = "\n\n---\n\n".join(
        USER_TEMPLATE.format(name=it["name"], singer=it["singer"], lyric=lyric_snippet(it["lyric"]))
        for it in items
    )
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.3,
        "max_tokens": 1800,
    }
    req = urllib_request(payload, key)
    out = json.loads(req)
    content = out["choices"][0]["message"]["content"]
    usage = out.get("usage", {})
    try:
        # 每首歌输出一个 JSON？为稳健：要求按歌曲顺序输出 JSON 数组
        data = json.loads(content)
        if isinstance(data, dict) and "songs" in data:
            return data["songs"], usage
        if isinstance(data, list):
            return data, usage
        # 单对象则套用到 batch 第一条
        return [data] + [{} for _ in items[1:]], usage
    except json.JSONDecodeError:
        return [{} for _ in items], usage


def urllib_request(payload: dict, key: str) -> str:
    import urllib.request

    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read().decode("utf-8")
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))


def enrich(conn: sqlite3.Connection, limit: int | None, key: str) -> tuple[int, int]:
    """批量标注，返回 (处理数, 成功数)。"""
    sql = "SELECT id, name, singer, lyric, genre, tag_source FROM songs WHERE mood_tags IS NULL"
    params: tuple = ()
    if limit:
        sql += " LIMIT ?"
        params = (limit,)
    rows = conn.execute(sql, params).fetchall()

    done = success = 0
    total_in_tokens = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        items = [
            {"id": r[0], "name": r[1], "singer": r[2], "lyric": r[3] or ""}
            for r in batch
        ]
        try:
            tags_list, usage = call_llm(key, items)
            total_in_tokens += usage.get("prompt_tokens", 0)
        except Exception as e:
            print(f"  批次失败: {e}", flush=True)
            time.sleep(3)
            continue

        for r, tags in zip(batch, tags_list):
            if not tags:
                continue
            sid, _, _, _, genre_existing, tag_source_existing = r
            mood = tags.get("mood_tags") or []
            scene = tags.get("scene_tags") or []
            genre = tags.get("genre") or genre_existing  # 已有真实 genre 则保留
            bpm = tags.get("bpm") or 0
            bpm = int(bpm) if 40 <= int(bpm) <= 200 else 0
            new_source = tag_source_existing if genre_existing else "llm"
            if tag_source_existing not in ("raw", "llm"):
                new_source = f"{tag_source_existing}+llm"
            conn.execute(
                "UPDATE songs SET mood_tags=?, scene_tags=?, bpm=?, genre=COALESCE(?, genre), "
                "tag_source=?, updated_at=? WHERE id=?",
                (
                    json.dumps(mood, ensure_ascii=False),
                    json.dumps(scene, ensure_ascii=False),
                    bpm,
                    genre,
                    new_source,
                    time.strftime("%Y-%m-%d"),
                    sid,
                ),
            )
            success += 1
        done += len(batch)
        if (i // BATCH_SIZE + 1) % 5 == 0:
            conn.commit()
            print(f"  [{done}/{len(rows)}] 成功 {success}", flush=True)
        time.sleep(0.5)

    conn.commit()
    return done, success, total_in_tokens


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--full", action="store_true")
    args = ap.parse_args()

    key = get_api_key()
    conn = sqlite3.connect(DB_PATH)
    limit = None if args.full else args.limit
    done, success, in_tokens = enrich(conn, limit, key)
    # 成本估算：deepseek-chat 约 $0.14/M 输入
    est_cost = in_tokens / 1_000_000 * 0.14
    print(f"\n处理 {done} 首, 成功 {success} 首, 输入 tokens {in_tokens}, 预估成本 ${est_cost:.4f}")
    conn.close()
