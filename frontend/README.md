# frontend · WorkMusic 工作台

> 本目录是 M4 里程碑（W11 D1–3）的产物，当前为占位。
> 规格见 docs/milestones.md M4 与 docs/prd.md §5/§6.5。

## 规划

- **T-401 工作台壳**：React + Vite + SSE 流式 Chat UI + Agent 切换；左侧任务树（@ 拉入群 + 活跃 Agent 指示）
- **T-402 结果卡片与 Citation 双栏联动**：检索结果卡片（命中理由）+ 点击跳转高亮原文
- **T-403 右栏工作区可视化**：搜索状态对象实时渲染、已选清单、会话成本

## 技术栈约定

- TypeScript（strict）+ React 18 + Vite
- SSE 客户端消费后端统一协议
- 代码规范见 docs/conventions.md

> 由 Agent 在 M4 启动时初始化脚手架（Vite + TS），禁止提前搭建避免半成品。
