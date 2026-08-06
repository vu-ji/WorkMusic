---
name: lyrics-pipeline
description: ChineseLyrics 数据管线工作流——10 万真实歌词清洗、SQLite 入库、元数据回填（DeepSeek 推断标签/BPM + 网易云真实热度），无合成字段。W10 里程碑 M1 的核心任务。用到搜索选曲（search_catalog）前必须先完成本管线。
---

# Lyrics Data Pipeline

WorkMusic 曲库数据管线（M1，W10 D1–2）。目标：把 102,197 首真实中文歌词清洗入库到 SQLite，并回填可用于检索的元数据（mood/scene/genre/bpm/language/popularity）。

**铁律（2026-08-06 用户决策）**：数据全用真实（ChineseLyrics + 真实回填 + LLM 基于歌词推断），**禁止合成/mock 字段**（license/price 等虚构业务字段已取消）。

## 数据源

- 仓库：[dengxiuqi/ChineseLyrics](https://github.com/dengxiuqi/ChineseLyrics)（5 个 JSON 文件，字段 `name / singer / lyric`，共 102,197 首）
- 下载后放入 `backend/data/raw/`，不提交进 git（.gitignore 已排除 backend/data/）

## 架构（真实优先三层）

1. **真实层**：歌词清洗入库（去重/空值/杂质行剔除）→ SQLite `data/workmusic.db`
2. **真实回填层**：网易云 API 回填 popularity（真实热度，中文名匹配；受风控限速）
3. **推断标注层（LLM）**：DeepSeek 基于歌词推断 mood_tags/scene_tags/genre/bpm（tag_source=llm）

最终 schema：`id, name, singer, lyric, lyric_lines, release_year, language, genre, bpm, mood_tags, scene_tags, popularity, tag_source(raw|llm|netease)`

## 执行步骤

### 1. 清洗 + 入库（clean.py → import_db.py）
```bash
cd backend
python data_pipeline/clean.py        # → data/clean/lyrics_clean.jsonl（≥9 万条）
python data_pipeline/import_db.py    # → data/workmusic.db（songs 表，全量）
```
- 清洗要点：歌名去《》/demo 后缀（先剥后缀再处理《》）；歌词过滤非歌词行（段落标记/作曲/演唱/G调/x2）
- 实测：102,198 → 100,504 条

### 2. 元数据回填
```bash
python data_pipeline/enrich_llm.py --limit 50      # DeepSeek 推断标注（先小样本验证）
python data_pipeline/enrich_llm.py --full          # 全量（约 10 万首 ≈ 10 小时，成本 ~$2）
python data_pipeline/enrich_netease.py --limit 200 # 网易云 popularity（受风控，间隔 2s+退避）
python data_pipeline/enrich_netease.py --full
```
- **LLM 标注契约**：prompt 要求输出 **JSON 数组**（顺序对应输入歌曲）；批 10 首、max_tokens 1800、歌词截断 400 字符（中段副歌区）；bpm 守卫 40–200
- **网易云风控**：搜索接口 0.8s×100 次会触发 code 405，必须间隔 ≥2s + 405/460/462 退避 45s 起
- **iTunes 已弃用**：中文歌在 iTunes 是英文名（Jay Chou/Nocturne），中文匹配必然失败（见 docs/pitfalls.md）

### 3. 检索使用
- 结构化过滤字段：bpm / genre / mood_tags / scene_tags / language / popularity
- 歌词对外仅取 ≤2 句片段（版权红线）

## 版权合规（红线）

- 歌词仅本地开发；对外部署版只展示 ≤2 句片段
- 入库字段保留 tag_source 溯源（真实/推断来源可审计）

## 验收（M1 完成定义）

- [x] 清洗后有效歌曲 ≥ 9 万（实测 100,504）
- [x] SQLite 全量入库 + 最小测试
- [ ] LLM 标注覆盖 ≥ 2 万首且抽检一致率 ≥ 85%（全量后台跑中）
- [ ] 无合成字段（license/price 已取消）
- [ ] pytest 全绿
