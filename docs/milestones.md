# WorkMusic 里程碑与任务清单

> 本文件是**唯一事实来源**（source of truth）。Agent 每完成一个任务就勾选 `[x]` 并标注完成日期。
> 任务编号格式 `T-xxx`，对应 PRD 里程碑（docs/prd.md §11）。
> 验收标准必须可测；未达标不勾选。

---

## M1 · 数据管线（W10 D1–2，目标 2026-08-08）

> 详细工作流见 skill：`.pi/skills/lyrics-pipeline/SKILL.md`

- [x] **T-101 数据下载与清洗**：ChineseLyrics 下载入库（去重/空值/异常），有效歌曲 ≥ 9 万。产出 `backend/data/clean/lyrics_clean.jsonl` + `backend/data_pipeline/clean.py` + 最小测试（2026-08-06：100,504 首，9 测试全绿）
- [x] **T-102 元数据回填管线**：真实歌词入库 SQLite（`import_db.py`，100,504 首）；bpm/mood/scene/genre 由 DeepSeek 基于歌词推断标注（`enrich_llm.py`，tag_source=llm，批 10 首 JSON 数组输出）；popularity 由网易云真实回填（`enrich_netease.py`，受风控限制慢速跑）。（2026-08-06：管线就绪，全量标注后台进行中）
- [ ] **T-103 合成业务字段**：~~license/price 合成~~ **已取消（用户决策：不用 mock 数据）**。检索约束调整为真实字段（bpm/mood/scene/genre/language/popularity）
- [ ] **T-104 合同模板（埋雷）**：5–8 份 PDF（单曲/批量/独家买断/公播/短视频），故意埋 10 个风险条款；埋雷清单存档为合同哨兵评估集。产出 `backend/data_pipeline/contract_templates/` + `docs/eval/contract-mines.md`

**M1 验收**：pytest 全绿；`lyrics_clean.jsonl` ≥ 9 万条；SQLite 全量入库（✓ 100,504）；LLM 标注覆盖 ≥ 2 万首且抽检一致率 ≥ 85%；无合成字段。

---

## M2 · RAG 底座（W10 D3–5，目标 2026-08-11）

> 模块：chunker / embedder / vector_store / retriever（从零实现，每模块带最小测试）

- [ ] **T-201 pgvector 建库建表**：PG 兼业务库（工作区/观测），`lyrics` 表含向量列 + 结构化字段列
- [ ] **T-202 歌词入库**：embedding（BGE-M3 / 通义 API）+ 向量索引；歌词全文切片存储（对外仅取 ≤2 句）
- [ ] **T-203 混合检索**：向量 top-k × 结构化过滤（BPM/genre/mood/license_tier/region）→ Rerank；产出 `backend/app/rag/retriever.py`
- [ ] **T-204 Citation 机制**：每条检索结果带命中理由 + 标签来源（tag_source 溯源）；无引用不输出

**M2 验收**：`search_catalog` 工具可调通（结构化过滤 + 向量语义）；50 条标注查询 Recall@10 基线 ≥ 0.6；pytest 全绿。

---

## M3 · Agent Runtime 接入与工具（W10 D6–7，目标 2026-08-13）

> 模块：LLM 抽象层 / ReAct Runtime / ToolExecutor（从零实现，见 docs/architecture.md）

- [ ] **T-301 LLM 抽象层**：多厂商（DeepSeek/通义/Ollama）+ 负载均衡 + 故障转移 + 模型路由（意图分流：轻量/强模型）
- [ ] **T-302 曲库雷达 Agent**：系统提示 + 工具集（search_catalog / get_track_detail / get_similar_tracks / check_license_status / estimate_license_fee / generate_license_draft）+ 搜索状态对象（结构化约束记忆，diff 更新）
- [ ] **T-303 工具实现与校验**：JSON Schema 参数校验 + 错误重试 + 敏感操作（generate_license_draft）human-in-the-loop 确认
- [ ] **T-304 工作区上下文（blackboard）**：buyer_profile / selected_tracks / quote / contract_draft / review_report 持久化，读写经工具调用

**M3 验收**：Agent 可对话完成「找 10 首 BPM 120+ 健身背景乐」→ 追问改约束 → 出报价单全流程；pytest + e2e 测试全绿。

---

## M4 · 前端 UI（W11 D1–3，目标 2026-08-17）

- [ ] **T-401 工作台壳**：React + Vite + SSE 流式 Chat UI + Agent 切换；左侧任务树（@ 拉入群 + 活跃 Agent 指示）
- [ ] **T-402 结果卡片与 Citation 双栏联动**：检索结果卡片（命中理由）+ 点击跳转高亮原文
- [ ] **T-403 右栏工作区可视化**：搜索状态对象实时渲染（约束高亮「刚更新」）、已选清单、会话成本

**M4 验收**：浏览器可跑通 Demo 剧本前 3 步（找歌 → 追问 → 报价）；SSE 流式无断流。

---

## M5 · 合同哨兵 + 深度模式（W11 D4–5，目标 2026-08-19）

- [ ] **T-501 合同解析**：PDF 解析 + 条款边界感知分块（防条款跨块断裂）；条款级 embedding
- [ ] **T-502 合同哨兵 Agent**：extract_clauses / flag_risks / cite_source 工具；风险标注（级别 + 理由 + 条款定位 页+段落偏移）
- [ ] **T-503 深度模式（orchestrator）**：Planner 拆需求 → 曲库雷达 → 结算 → 合同哨兵 → 聚合报告；执行轨迹图实时可视。时间盒 2 天，做不完降级为架构图讲解（PRD 风险登记）

**M5 验收**：埋雷条款检出率（P/R）基线 ≥ 70%；合同哨兵可接手曲库雷达的工作区上下文完成审查（无需重复上传）。

---

## M6 · 结算 + 观测面板（W11 D6–7，目标 2026-08-21）

- [ ] **T-601 mock 结算页**：一页报价单（限 1 天，最先砍项）
- [ ] **T-602 观测/成本面板**：TTFT / token / 成本 / 延迟 / 模型路由记录；Prompt 版本管理（YAML + A/B + 回滚）

**M6 验收**：面板展示真实会话数据；Prompt 可版本化并可回滚。

---

## M7 · 评估 + 上线（W12，目标 2026-08-28）

- [ ] **T-701 评估集与自动化评测**：检索（50 条标注 Recall@10/MRR）+ 合同检出率 + LLM-as-judge（推荐语/摘要）+ 注入测试集
- [ ] **T-702 回归 CI**：Prompt 版本变更自动跑评估集，指标回退报警
- [ ] **T-703 部署上线**：对外部署版（歌词片段限制生效）+ 安全加固（注入过滤 / 解析沙箱 / 敏感操作确认）
- [ ] **T-704 面试案例库**：PRD §13 六条弹药逐条补齐（数据 + 截图 + 复盘）

**M7 验收**：评估报告产出；线上可访问；面试弹药全部可讲。

---

## 阻塞登记

| 任务 | 现象 | 尝试过的方案 | 状态 |
|---|---|---|---|
| — | — | — | — |

（遇到卡点在此登记，Agent 继续下一个可解任务，回头处理）
