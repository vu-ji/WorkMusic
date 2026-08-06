---
name: lyrics-pipeline
description: ChineseLyrics 数据管线工作流——10 万真实歌词清洗、LLM-as-tagger 打标（情绪/场景/风格/BPM）、合成业务字段、pgvector 入库。W10 里程碑 M1 的核心任务。用到搜索选曲（search_catalog）前必须先完成本管线。
---

# Lyrics Data Pipeline

WorkMusic 曲库数据管线（M1，W10 D1–2）。目标：把 102,197 首真实中文歌词变成可被混合检索（向量 + 结构化过滤）的曲库。

## 数据源

- 仓库：[dengxiuqi/ChineseLyrics](https://github.com/dengxiuqi/ChineseLyrics)（5 个 JSON 文件，字段 `name / singer / lyric`，另附词频/押韵表）
- 下载后放入 `backend/data/raw/`，不提交进 git

## 三层数据架构（PRD §8）

1. **真实层**：歌词清洗入库（去重/空值/异常处理）
2. **标注层（LLM-as-tagger）**：top 2–5 万首 LLM 打标（mood_tags / scene_tags / genre / language / bpm 估计）；取副歌截断批量请求，DeepSeek 成本可控；其余程序兜底 + 人工抽检
3. **业务层（纯合成）**：license_type / price_tier / authorized_regions / status / popularity 程序生成

最终 schema：`id, title, singer, lyric, mood_tags[], scene_tags[], genre, bpm, language, release_year, popularity, license_type, price_tier, authorized_regions[], status, tag_source(llm|synthetic)`

## 执行步骤

### 1. 清洗（clean.py）
- 去重（name+singer）、空 lyric 剔除、非法字符清洗
- 输出：`backend/data/clean/lyrics_clean.jsonl`

### 2. 打标（tag.py，LLM-as-tagger 管线）
- 只对 top 2–5 万首（按 popularity 预排序）
- 取副歌截断（中段 2–4 行，控制 token）
- 批量请求 DeepSeek，JSON mode 输出标签
- 失败重试（复用 W5 RetryController 思路）+ 其余歌曲程序兜底（基于关键词词频表）
- 抽检：每 1000 首抽 10 首人工校验，记录一致率
- 输出：`backend/data/tagged/lyrics_tagged.jsonl`

### 3. 合成业务字段（synthesize.py）
- 程序生成授权类型/价格档位/可授权区域/状态，可复现（固定 seed）
- 合并输出完整 schema

### 4. 入库（ingest.py）
- pgvector：建表 + embedding（BGE-M3 或通义 API，见 docs/architecture.md）+ 向量索引
- embedding 复用 W6 OllamaEmbedder 代码（git backup 分支 w6-rag/）
- 结构化字段进普通列，检索时 SQL 里同时过滤

## 版权合规（红线）

- 歌词仅本地开发；对外部署版只展示 ≤2 句片段
- 入库字段保留 tag_source 溯源

## 验收标准（M1 完成定义）

- [ ] 清洗后有效歌曲 ≥ 9 万首
- [ ] LLM 打标 ≥ 2 万首，抽检一致率 ≥ 85%
- [ ] 合成字段 10 万首全覆盖，可复现（同 seed 同结果）
- [ ] pgvector 入库完成，`search_catalog` 工具可返回结构化过滤 + 向量结果
- [ ] pytest 全绿（清洗/打标/合成各模块最小测试）

## 参考

- 详见 `docs/milestones.md` M1 任务拆分
- 踩坑记录同步到 docs/pitfalls.md（现象→根因→解法）
