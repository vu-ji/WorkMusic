# WorkMusic · 版权交易 Agent 工作台 · PRD

> 版本：v0.5（已拍板）｜ 日期：2026-07-25 ｜ 状态：进入执行
> v0.5 变更：交互模型重写为**群聊 + @Agent + 上下文接续 + 主 Agent 接管兜底**；左侧简化为「任务名 + 群成员」
> v0.4 变更：交互模型定稿——**聊天框即主 Agent，自动路由子 Agent，用户无感切换**；左侧 Agent 列表改为「当前活跃专家」指示器
> v0.3 变更：平台更名 **WorkMusic**；从「单 Agent 应用」升级为「工作台 + 专家团 Agent」架构（新增第 6.5 节专家团与数据串联）
> 对标方向：AI Agent 应用开发工程师（音乐版权/内容平台领域，第一主攻）

---

## 1. 一句话定义

**WorkMusic：一个音乐版权交易的 Agent 工作台**——类 WorkBuddy 产品形态，首批入驻两个专家 Agent：「曲库雷达」（语义选曲）与「合同哨兵」（合同审查），通过统一 SSE 协议与**共享工作区上下文**串联完整交易链路：找歌 → 报价（mock 结算）→ 审合同。

它不是 demo，是一个「3 分钟能讲完整商业故事」的平台型产品。

## 2. 为什么是这个项目

- **业务映射**：找歌 ≈ 曲库版权采买；审合同 ≈ 「智能合同处理」场景；结算 ≈ 「支付/结算系统」。
- **职责映射**：一个项目打满 AI Agent 应用开发的核心职责（见第 12 节覆盖矩阵）。
- **个人优势映射**：React 流式 UI + Citation 联动高亮 + 可视化面板 = 后端出身候选人做不出的前端降维打击。
- **实现路线**：RAG 底座、ReAct 组件、MCP 曲库工具等核心机制在 W10 从零实现，吸收此前学习阶段验证过的设计思路。

## 3. Demo 剧本（3 分钟，面试现场版）

1. **找歌**：用户在「曲库雷达」中输入「我要给连锁健身房找 10 首背景音乐，BPM 120+，副歌有爆发力，预算 5 万/年」→ Agent 拆解约束 → 混合检索 → 流式返回候选，每首附 Citation（命中理由 + 标签来源）。
2. **追问**：「第 3 首换成女声」→ 会话记忆 + 约束追加（右栏搜索状态对象实时高亮「女声 · 刚更新」）。
3. **结算**：「就出这三首的授权方案」→ mock 报价单 + 合同草稿生成 → **主 Agent 自动转交**：左侧绿灯跳到「合同哨兵」，提示「已为你转交合同哨兵审查」。
4. **审合同（压轴）**：合同哨兵接手（工作区上下文自动带入，无需重复上传）→ 风险条款标红 → **点击任意结论跳转到合同原文段落并高亮**。
5. **深度模式**（可选高潮）：重新发问 → 主 Agent（orchestrator）自动路由全流程：曲库雷达找歌 → 结算 → 合同哨兵审查 → 汇总报告，React 实时执行轨迹图。
6. **收尾**：打开观测面板——本次会话的 TTFT、token 成本、模型路由记录一目了然。

## 4. 功能范围（MVP 切法）

| 阶段 | 内容 | 时间盒 | 砍线预案 |
|---|---|---|---|
| **Phase A（底线，必保）** | 曲库雷达：约束拆解 + 混合检索 + 单 Agent 对话 + SSE 流式 UI + Citation | W10 全程 | 任何情况不砍 |
| **Phase B（高潮，力保）** | 合同哨兵：合同解析 + 条款提取 + 风险标注 + 双栏原文联动高亮 | W10 末–W11 | 时间紧先砍 C 保 B |
| **Phase C（加分，限 1 天）** | mock 结算页（一页报价单，不做支付流） | W11 | 最先砍 |
| **Phase D（贯穿）** | 观测/成本面板 + Prompt 版本管理 | W11 | 砍为只读日志页 |
| **Phase E（冲刺，限 2 天）** | Multi-Agent 深度模式 + 执行轨迹可视化 | W11 | 做不完砍，降级为架构图讲解 |

## 5. 系统架构

```
WorkMusic 工作台壳（React + Vite）
  ├─ Agent 列表/切换 · 流式 Chat UI · Citation 双栏联动 · 执行轨迹图 · 观测面板
  └─ 右栏：工作区上下文可视化（搜索状态对象 / 已选清单 / 会话成本）
        │  统一 SSE/WebSocket 协议 + Agent 注册表（endpoint / capabilities / 会话路由）
        ▼
Agent 服务层（Python FastAPI + 手写 Runtime）
  ├─ 曲库雷达 Agent：search_catalog / get_track_detail / check_license / estimate_fee
  ├─ 合同哨兵 Agent：parse_contract / extract_clauses / flag_risks / cite_source
  ├─ 主 Agent（orchestrator，深度模式 P1）：按流程路由两个专家并聚合结果
  └─ 共享：LLM 抽象层（多厂商/负载均衡/故障转移/模型路由）
           · Prompt 版本管理（YAML + A/B + 回滚）
           · pgvector RAG 底座（PG 兼业务库：工作区 + 观测数据）
           · Redis（Prompt/检索缓存 + Streams 打标队列）· 观测（tokens/成本/延迟 → 面板）
        │
        ▼
工作区上下文（Workspace / blackboard，FastAPI 侧持久化）
  buyer_profile · selected_tracks · quote · contract_draft · review_report
  —— Agent 间唯一数据通道，全部读写经工具调用完成（可观测、可回放）
```

**关键决策（可 challenge）**：
- **向量库选 pgvector**：「BPM/价格结构化过滤 + 向量语义」在一个 SQL 里完成，混合检索最干净。备选 Qdrant。PG 同时兼业务库（工作区、观测数据），不引入第二个存储。
- **Agent Runtime 手写**（从零实现），不套 LangGraph——面试话术：「runtime 是我自己写的，我清楚每一层为什么存在」。工作流编排展示用 LangGraph 画深度模式即可。
- **后端 FastAPI**：Python 服务端技术栈，W1–W3 已用 Python 练手。
- **Redis 一个实例两个用途**（v0.4 新增）：① Prompt/检索结果缓存（职责⑤「智能缓存：Prompt 缓存、向量缓存」，缓存层先抽象接口、Redis 可替换）② Redis Streams 作为 LLM-as-tagger 打标管线队列（5 万首异步打标，天然削峰）。**不单独上 RabbitMQ/Kafka**——单机规模下运维成本不划算，选型评估过程写进笔记（同时覆盖「Redis、消息队列」等基础能力要求）。
- **Agents 列表树状化**（v0.4 新增）：主 Agent 为父节点、专家为子节点，表达 orchestrator→specialist 调度关系；绿灯在树上跳动 = 调度轨迹可视化。

## 6. Agent 设计

**标准模式**：每个专家 Agent 内部 = 单 Agent + ReAct 循环（思考→调工具→观察→再思考），推理模式组件化可切换（ReAct/CoT/ToT）。

**深度模式**（Phase E）：主 Agent（orchestrator）自动路由全流程：Planner 拆需求 → 曲库雷达检索 → 结算工具 → 合同哨兵审查 → 聚合汇总，轨迹图实时可视。

### 6.5 专家团架构与数据串联（v0.3 新增）

**为什么是两个独立 Agent 而不是一个大 prompt**——专家团模式（类 WorkBuddy 专家中心）：每个专家有独立的 system prompt、工具集、记忆结构、评估集。好处：prompt 各自聚焦（找歌的不需要懂合同法）、工具权限最小化、评估可独立进行、新专家可插拔（未来加「宣发官」「星探」不动现有代码）。

| | 曲库雷达 | 合同哨兵 |
|---|---|---|
| 职责 | 语义选曲、约束拆解、授权询价 | 合同解析、条款提取、风险标注 |
| 工具 | search_catalog / get_track_detail / get_similar / check_license / estimate_fee / generate_license_draft | parse_contract / extract_clauses / flag_risks / cite_source |
| 记忆 | 搜索状态对象（结构化约束） | 合同上下文（条款索引 / 审查进度） |
| 评估集 | 50 条标注查询 Recall@10 | 埋雷条款检出率（P/R） |

**数据串联：共享工作区上下文（blackboard 模式）**——两个 Agent 不直接对话，一切交接经工作区完成：

```
曲库雷达 写入 selected_tracks + buyer_profile
  → 结算工具 生成 quote + contract_draft
    → 合同哨兵 读取 contract_draft、写回 review_report
```

工作区由工作台壳持有并实时渲染到右栏（用户全程可见）。前端类比：**微前端 + 全局 store**——每个 Agent 是独立应用，工作区是共享状态层；读写全部走工具调用，天然可观测、可回放。

**左侧导航：任务树 + 按需成员（v0.5 终稿）**：Agent 默认不显示——**@ 即拉入群**，被 @ 过的 Agent 才挂到对应任务下。任务按最近活跃排序，当前任务置顶。每个任务的子成员 = 该对话中调用过的 Agent 清单，当前对话者高亮 +「当前」badge。逻辑：新任务成员列表为空 → 首次 @曲库雷达 → 曲库雷达出现 → @合同哨兵 → 合同哨兵加入 → 即使话题结束，成员留存（历史成员可随时再 @）。

**路由与上下文续接**：`@Agent` 设 `active_agent`，后续消息无需再 @ 默认发给它；话题切换时重新 @ 换人；主 Agent 在后台监听，**当消息与 active_agent 无关时自动接管**（轻量提示「话题切换 · 主 Agent 接管」）+ 提供回切建议。输入区顶部显示「当前发送给：XX · 切换」。——**一句话面试话术：「@谁谁干活，接着聊不用 @，话题跑偏主 Agent 兜底。」**实现上主 Agent 复用 Runtime，路由 = `@mention 解析 → 设 active_agent → 意图兜底`，单 SSE。

**工具清单（JSON Schema，示例）**：
- `search_catalog(query, filters{bpm_min,bpm_max,genre,mood,language,license_tier,max_price}, top_k)`
- `get_track_detail(track_id)` / `get_similar_tracks(track_id, top_k)`
- `check_license_status(track_id, region, usage_type)`
- `estimate_license_fee(track_ids, usage_type, duration_years, region)`
- `generate_license_draft(track_ids, buyer_info)` ⚠️ 敏感操作，需用户确认（human-in-the-loop）
- `parse_contract(file_id)` / `extract_clauses(doc_id)` / `flag_risks(clauses)` / `cite_source(clause_id)`

**记忆设计（工程亮点）**：用户追加的约束不显式塞对话历史，而是维护一个**结构化「搜索状态对象」**（当前全部约束 + 已选曲目 + 预算），每轮 diff 更新——比通用文本压缩更稳，面试有得讲。长期记忆：历史偏好画像，会话恢复时注入。

## 7. RAG 设计

- **曲库侧**：10 万+ 真实中文歌词（ChineseLyrics，见第 8 节）+ LLM 打标 + 程序生成业务字段；索引 = 歌词片段 + 描述文本 embedding（BGE-M3 本地或通义 embedding API）+ 结构化字段；检索 = 向量 top-k × 结构化过滤 → Rerank。
- **合同侧**：PDF 解析（条款边界感知分块，防条款跨块断裂）→ 条款级 embedding；**Citation 定位到页 + 段落偏移**，前端双栏联动高亮。
- **幻觉防线**：所有推荐/审查结论必须挂 Citation，无引用不输出；评估集专测「引用忠实度」。

## 8. 数据方案（v0.2 更新：真实歌词 + 合成业务字段）

**底座数据（用户指定）**：[dengxiuqi/ChineseLyrics](https://github.com/dengxiuqi/ChineseLyrics)——102,197 首真实中文歌词（4019 位歌手，2019 年前的华语歌），5 个 JSON 文件，字段 `name / singer / lyric`，另附词频表与押韵表（可用于扩展玩法）。

**三层数据架构**：
1. **真实层**：歌词库清洗入库（去重/空值/异常处理）——真实感来源。
2. **标注层（LLM-as-tagger 管线）**：对 top 2–5 万首做 LLM 打标（情绪/场景/风格/语言/BPM 估计；取副歌截断批量请求，DeepSeek 成本可控）；其余程序兜底 + 人工抽检。该管线本身是数据工程亮点。
3. **业务层（纯合成）**：授权类型/价格档位/可授权区域/状态等字段程序生成挂接——虚构业务数据，无所谓真假。

**最终 schema**：`id, title(name), singer, lyric, mood_tags[], scene_tags[], genre, bpm, language, release_year, popularity, license_type, price_tier, authorized_regions[], status, tag_source(llm|synthetic)`

**版权合规声明（面试红线，必须执行）**：
- 该歌词库标注「仅供学习交流使用」，歌词版权属原版权方。**在版权公司面试时这是敏感点，必须主动处理**：
- 本地开发可用；对外部署版**只展示歌词片段（≤2 句），不展示/不出接口返回完整歌词**；
- README 显著位置声明数据来源、用途与版权立场；
- 面试话术主动讲：「真实场景这里应接正版曲库 API，歌词仅用于检索验证」——把合规意识变成加分项。

**合同模板 5–8 份**（单曲授权 / 批量授权 / 独家买断 / 公播 / 短视频授权），每份 5–10 页 PDF——**故意埋 10 个风险条款**（自动续约、地域漏洞、分成模糊、授权范围过宽等）。埋雷清单单独存档，作为合同哨兵的检出率评估集。这是演示效果的核武器。

## 9. 性能与成本（职责⑤）

- TTFT：SSE 流式 + 首 token 优化（系统提示缓存、检索结果摘要化）。
- 模型路由：意图分流——闲聊/简单问答走轻量模型（DeepSeek-chat），复杂推理走强模型；失败按「贵→贱」Fallback。
- 成本面板：每次调用记录 model/tokens/成本/延迟，React 面板展示单会话与累计账单——面试话术：「我清楚每 1000 次调用的账单金额」。

## 10. 评估体系（W12，职责⑥）

- **检索**：50 条标注查询，Recall@10 / MRR。
- **合同审查**：埋雷条款检出率（precision/recall）——有标准答案，最硬。
- **生成**：LLM-as-judge 评推荐语/合同摘要（准确性 + 引用忠实度）。
- **回归 CI**：Prompt 版本变更自动跑评估集，指标回退报警；Prompt 注入测试集（「忽略之前指令」类）。
- **安全**：输入注入过滤层；合同文件解析沙箱隔离；敏感操作（生成合同/报价）必须人工确认。

## 11. 里程碑（对齐 W10–W12）

| 时间 | 交付 |
|---|---|
| W10 D1–2 | 数据管线（ChineseLyrics 清洗 + LLM 打标 + 业务字段生成）+ 合同模板（埋雷） |
| W10 D3–5 | RAG 底座（pgvector 入库、混合检索、Citation） |
| W10 D6–7 | Agent 运行时接入 + 工具实现 |
| W11 D1–3 | React 对话 UI（SSE、结果卡片、Citation 联动） |
| W11 D4–5 | 合同哨兵 + 双栏高亮；深度模式（时间盒 2 天） |
| W11 D6–7 | 结算页（1 天）+ 观测/成本面板 |
| W12 | 评估集 + 回归 CI + 部署上线 + 面试案例库整理 |

## 12. 职责覆盖矩阵

| 核心职责 | 落点 |
|---|---|
| ① React 流式界面 + Python 运行时 + 记忆/压缩 + ReAct/CoT 组件化 | 前端 + Runtime + 搜索状态对象 + Phase E |
| ② 多厂商 LLM 抽象层 + Function Calling 工具生态 + Prompt 版本管理 | LLM 抽象层 + 工具清单 + Phase D |
| ③ RAG 全套 + Citation + 多租户/权限 | 曲库/合同双 RAG + 双栏高亮（多租户做 mock 角色切换，轻实现） |
| ④ Multi-Agent + 工作流编排 | 深度模式 + LangGraph 轨迹图 |
| ⑤ TTFT/缓存/成本/模型路由/可观测 | 第 9 节 + 成本面板 |
| ⑥ 测试链/注入检测/沙箱/CI | 第 10 节 |

## 13. 面试弹药（30 分钟 code review 候选题目）

1. 10 万真实歌词混合检索召回漂移的根因与调参实录
2. 合同条款跨块断裂问题与分块策略重设计
3. 「搜索状态对象」替代通用上下文压缩的权衡
4. 埋雷条款检出率从 60% 优化到 90% 的过程
5. Prompt 版本回滚救了一次线上质量事故（A/B 实测）
6. LLM-as-tagger 给 5 万首歌打标：成本、一致性与抽检

**博客选题储备**：《我给音乐版权交易做了一个 Agent》《10 万真实歌词混合检索调参实录》《Citation 联动高亮的前端实现》《95% AI 生成代码，我是怎么做 Review 的》

## 14. 风险登记

| 风险 | 等级 | 缓解 |
|---|---|---|
| 范围蔓延，两头 70 分 | 高 | MVP 切法 + 砍线预案（第 4 节），A 永远优先 |
| Multi-Agent 失控/超时 | 中 | 时间盒 2 天，做不完降级为架构图讲解 |
| mock 数据太假被看穿 | 中 | 歌词片段 LLM 精修 2000 条；合同请 AI 起草后人工改两轮 |
| 评估主观（配方/推荐好坏） | 中 | 以合同检出率（有标准答案）为硬指标，生成类用 judge 软指标 |
| 工期挤压（只有 2 周） | 高 | 底座实现一次到位，W10 不返工 |

---

**开放问题（2026-07-25 已全部拍板）**：
1. ✅ 向量库：pgvector（结构化过滤 + 向量检索一体）。
2. ✅ 深度模式 Multi-Agent：保留，时间盒 2 天，做不完降级为架构图讲解。
3. ✅ mock 结算页：保留，限 1 天，一页报价单。
4. ✅ 数据底座：dengxiuqi/ChineseLyrics 真实歌词库（三层数据架构 + 合规声明见第 8 节）。
5. ✅ 平台命名：**WorkMusic**（v0.3，弃用「版权交易工作台」）。
6. ✅ Agent 架构：**专家团模式**（曲库雷达 + 合同哨兵独立 Agent + 共享工作区上下文 blackboard；深度模式 = orchestrator 自动路由）。
