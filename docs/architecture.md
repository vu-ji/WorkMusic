# 架构说明（Architecture）

> 详细 PRD：docs/prd.md（v0.5 已拍板）。本文档是架构图 + 关键设计决策的速查，给 Agent 和 reviewer 用。

## 1. 总体架构

```
┌─────────────────────────────────────────────────────────┐
│  前端工作台（React + Vite）                                │
│  · 流式 Chat UI（SSE） · Agent 列表/切换 · Citation 双栏    │
│  · 执行轨迹图（深度模式） · 观测面板（成本/token/TTFT）      │
└──────────────────────┬──────────────────────────────────┘
                       │ 统一 SSE/WS 协议 + Agent 注册表
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Agent 服务层（Python FastAPI + 手写 Runtime）             │
│  ├─ 曲库雷达（curator）：search/check/estimate/generate    │
│  ├─ 合同哨兵（sentinel）：parse/extract/flag/cite          │
│  ├─ 主 Agent（orchestrator，深度模式）：路由+聚合            │
│  └─ 共享：LLM 抽象层 · Prompt 版本管理 · 观测               │
└───────────────┬──────────────────────┬──────────────────┘
                ▼                      ▼
        ┌───────────────┐      ┌───────────────┐
        │  PostgreSQL    │      │    Redis      │
        │  pgvector 向量 │      │  Prompt/检索缓存│
        │  + 业务库(工作区/观测)│   │  + Streams 打标队列│
        └───────────────┘      └───────────────┘
```

## 2. 核心设计决策（PRD 可 challenge 项 → 已拍板）

| 决策 | 理由 | 前端类比 |
|---|---|---|
| pgvector（不用 Qdrant/Chroma） | 结构化过滤+向量一个 SQL；PG 兼业务库 | 单库 = 单数据源，避免多存储同步 |
| 手写 Runtime（不套 LangGraph） | 面试讲得清每一层；W8 产物直接演化 | 自己写事件循环 vs 用框架 |
| 专家团架构（独立 Agent + blackboard） | prompt 聚焦 / 权限最小 / 评估独立 / 可插拔 | 微前端 + 全局 store |
| 搜索状态对象（结构化记忆） | 比通用文本压缩稳，约束 diff 更新 | 受控组件 vs 非受控 DOM |
| Redis 一实例两用 | 缓存 + Streams 打标队列；单机不引 MQ | 一个进程内 shared state + 任务队列 |

## 3. Agent 运行时（复用 W8 react.py）

```
循环：思考(LLM) → 工具调用(JSON Schema 校验) → 观察 → 再思考
  · 推理模式组件化：ReAct（默认）/ CoT / ToT
  · 工具错误重试（复用 W5 RetryController）
  · 敏感工具（generate_license_draft）→ 用户确认 gate
  · 记忆：短期对话 + 长期偏好画像；曲库雷达用「搜索状态对象」diff 更新
```

## 4. RAG 设计

- **曲库侧**：歌词片段 + 描述文本 embedding（BGE-M3 / 通义）→ 向量 top-k × 结构化过滤（BPM/genre/mood/price/region）→ Rerank
- **合同侧**：PDF → 条款边界感知分块（防跨块断裂）→ 条款级 embedding；Citation 定位到 页+段落偏移
- **幻觉防线**：无引用不输出；评估集专测引用忠实度

## 5. 数据链路

```
ChineseLyrics(10万) ──clean──> 清洗层 ──LLM打标(tag)──> 标注层(2-5万首)
      └──synthesize──> 业务字段(license/price/region) ──ingest──> pgvector
工作区(blackboard)：buyer_profile → selected_tracks → quote+contract_draft → review_report
```

## 6. 关键接口（工具清单，JSON Schema）

```
search_catalog(query, filters{bpm_min,bpm_max,genre,mood,language,license_tier,max_price}, top_k)
get_track_detail(track_id) / get_similar_tracks(track_id, top_k)
check_license_status(track_id, region, usage_type)
estimate_license_fee(track_ids, usage_type, duration_years, region)
generate_license_draft(track_ids, buyer_info)   # ⚠️ 需用户确认
parse_contract(file_id) / extract_clauses(doc_id) / flag_risks(clauses) / cite_source(clause_id)
```

## 7. 观测指标（职责⑤）

- TTFT / token / 成本 / 延迟：每次 LLM 调用记录 → 成本面板
- 模型路由：意图分流（轻量 DeepSeek-chat ↔ 强模型）+ 失败「贵→贱」Fallback
- Prompt 版本管理：YAML + A/B + 回滚，变更自动跑评估集（M7）
