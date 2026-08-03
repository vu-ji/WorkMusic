# W8 · Agent 架构（Phase 4）

手写两种 Agent 范式 + MCP server 接入 + 多轮记忆。

## 目录

```
src/
├── react.py          # ReAct 范式（思考→行动→观察）
├── plan_execute.py   # Plan-Execute 范式（先计划再执行）
├── memory.py         # 多轮记忆（短期 + 长期）
└── test_agent_arch.py # pytest 测试
```

## 跑

```bash
make test
```

## 三种范式的演进

| 范式 | 核心 | 适用场景 | 前端类比 |
|---|---|---|---|
| W4 Agent Loop | action → 执行 → 回复 | 单次工具调用 | dispatch + reducer |
| W8 ReAct | 思考→行动→观察 循环 | 需要多步探索 | 事件循环 + 决策日志 |
| W8 Plan-Execute | 先计划再执行 | 复杂任务拆解 | TODO list + 逐个完成 |

## 复用清单

| 组件 | 来源 | 用途 |
|---|---|---|
| RouterClient | W1 | LLM 调用 |
| ToolExecutor + search_catalog | W4 | 工具执行 |
| RetryController | W5 | 网络重试 |
| HybridRetriever | W6 | 知识检索（可选）|
