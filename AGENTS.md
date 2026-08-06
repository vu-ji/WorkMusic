# AGENTS.md · WorkMusic 项目说明书

> 本文件是项目的**出生证明**。任何 Agent（包括 Pi）进入本仓库，请先读完本文件与 `docs/` 下的规格文档，再开始工作。
> 维护规则：每次任务完成后，更新「当前状态」与 `docs/milestones.md` 的勾选进度。

---

## 1. 项目身份

**WorkMusic：一个音乐版权交易的 Agent 工作台**——类 WorkBuddy 产品形态，首批入驻两个专家 Agent：「曲库雷达」（语义选曲）与「合同哨兵」（合同审查），通过统一 SSE 协议与**共享工作区上下文**串联完整交易链路：**找歌 → 报价（mock 结算）→ 审合同**。

- 对标方向：AI Agent 应用开发工程师（音乐版权/内容平台领域）
- 项目定位：不是 demo，是一个「3 分钟能讲完整商业故事」的平台型产品
- 当前阶段：W10 毕业冲刺（W10–W12），2026-08-06 从零重建（main 分支已清空）

## 2. 当前状态

- **当前里程碑**：M1 数据管线（W10 D1–2，计划 2026-08-08 完成）
- **任务清单**：见 [`docs/milestones.md`](docs/milestones.md)（唯一事实来源，勾选即进度）
- **可复用代码**：W1–W9 学习产物保存在 git `backup` 分支，动手前必查 [`docs/reuse-map.md`](docs/reuse-map.md)

## 3. 架构总览（详见 docs/architecture.md）

```
WorkMusic 工作台壳（React + Vite）
  ├─ Agent 列表/切换 · 流式 Chat UI · Citation 双栏联动 · 执行轨迹图 · 观测面板
  └─ 右栏：工作区上下文可视化（搜索状态对象 / 已选清单 / 会话成本）
        │  统一 SSE/WebSocket 协议 + Agent 注册表（endpoint / capabilities / 会话路由）
        ▼
Agent 服务层（Python FastAPI + 手写 Runtime，W8 产物复用）
  ├─ 曲库雷达 Agent：search_catalog / get_track_detail / check_license / estimate_fee
  ├─ 合同哨兵 Agent：parse_contract / extract_clauses / flag_risks / cite_source
  ├─ 主 Agent（orchestrator，深度模式 P1）：按流程路由两个专家并聚合结果
  └─ 共享：LLM 抽象层（多厂商/负载均衡/故障转移）· Prompt 版本管理
           · pgvector RAG 底座 · Redis（缓存 + Streams 打标队列）· 观测（tokens/成本/延迟）
        ▼
工作区上下文（Workspace / blackboard，FastAPI 侧持久化）
  buyer_profile · selected_tracks · quote · contract_draft · review_report
  —— Agent 间唯一数据通道，全部读写经工具调用完成（可观测、可回放）
```

## 4. 不可挑战的关键决策（已拍板，见 docs/prd.md）

| # | 决策 | 原因 |
|---|---|---|
| 1 | 向量库用 **pgvector**（不换 Qdrant） | 结构化过滤 + 向量检索一个 SQL 完成；PG 兼业务库 |
| 2 | **Agent Runtime 手写**（复用 W8），不套 LangGraph | 面试话术：「runtime 是我自己写的，我清楚每一层为什么存在」 |
| 3 | **专家团架构**：两个独立 Agent + blackboard 工作区 | prompt 各自聚焦、工具权限最小化、评估独立、新专家可插拔 |
| 4 | mock 结算只做**一页报价单**，不做支付流 | 时间盒 1 天，最先砍 |
| 5 | 数据底座 **ChineseLyrics** 10 万真实歌词 + LLM 打标 + 合成业务字段 | 真实感来源 + 数据工程亮点 |

## 5. 开发规范（详见 docs/conventions.md）

- **语言**：后端 Python（FastAPI），前端 TypeScript/React（Vite）
- **测试**：pytest，每个模块最小测试；验收标准可测才算完成
- **Commit**：Conventional Commits（`feat|fix|refactor|docs|chore|test` + scope）
- **文档**：模块级 README + `.env.example`（禁止提交真实密钥）
- **注释/汇报**：中文；技术名词保留英文原文（context window、grounding、blackboard）
- **复用优先**：动手前先查 `docs/reuse-map.md`；复用不等于糊里糊涂地用，要写清设计取舍

## 6. 版权合规红线（面试红线，必须执行）

- ChineseLyrics 歌词库标注「仅供学习交流使用」，版权属原版权方
- **对外部署版只展示歌词片段（≤2 句）**，不出接口返回完整歌词
- README 显著位置声明数据来源、用途与版权立场
- 面试话术：真实场景应接正版曲库 API，歌词仅用于检索验证

## 7. 工作流程（本 harness 如何驱动你）

1. **每轮工作开始**：读本文件 + `docs/milestones.md`，确认当前任务（T-编号）
2. **任务执行循环**（模板见 `.pi/prompts/`）：
   - `PLAN` → 写清楚：做什么 / 改哪些文件 / 怎么验收 / 风险
   - `IMPLEMENT` → 动手写代码（复用优先，查 reuse-map）
   - `VERIFY` → 跑测试、自检验收标准
   - `COMMIT` → 遵守 commit 规范，更新 `docs/milestones.md` 勾选
3. **一个任务完成后**：简短汇报（做了什么 / 验收结果 / 下一步），再进入下一个任务
4. **遇到阻塞**：不要硬编。把阻塞写进 milestones.md 的备注，说明尝试过的方案，继续下一个可解任务

## 8. 常用命令

```bash
# 后端
cd backend && uv pip install -r requirements.txt   # 或 pip install -r requirements.txt
cd backend && python -m pytest                      # 跑测试

# 前端（M3 起）
cd frontend && npm install && npm run dev
```
