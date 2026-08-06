# 复用地图（Reuse Map）· W1–W9 产物 → WorkMusic

> W1–W9 全部学习产物保存在 git **`backup` 分支**。本文件是「动手前必查」的复用索引。
> 恢复方式：`git checkout backup -- <路径>` 或整体 `git checkout backup` 查看。
> 复用铁律：复用不等于糊里糊涂地用——每个模块迁移后，要在代码注释/笔记中写清「原设计取舍 + 我做了哪些调整 + 为什么」。

## 映射总表

| WorkMusic 模块 | 复用来源（backup 分支） | 迁移要点 |
|---|---|---|
| LLM 抽象层（多厂商/负载均衡/故障转移） | `w3-context/src/token_budget.py`（RouterClient 对话路由） | 扩展为多 provider 注册表 + 意图分流 |
| Token 预算与上下文管理 | `w3-context/src/token_budget.py`（TokenBudget 三方法） | 直接迁移 + 适配 FastAPI 异步 |
| 工具注册/参数校验 | `w4-tool-use/src/tool_registry.py`、`tool_schema.py` | 直接迁移，补 JSON Schema 校验 |
| 工具执行器（Agent Loop） | `w4-tool-use/src/tool_executor.py`、`agent.py` | 迁移 + 适配 W8 Runtime |
| 错误重试 | `w5-error-retry/src/retry_controller.py`（RetryController） | 直接迁移，LLM-as-tagger 管线复用 |
| 文本切分 | `w6-rag/src/chunker.py` | 合同侧需「条款边界感知分块」，重写分块策略 |
| Embedding | `w6-rag/src/embedder.py`（Ollama bge-m3，1024 维） | 保留 Ollama 本地 + 加通义 API 双通道 |
| 向量存储 | `w6-rag/src/vector_store.py`（Chroma 1.5.9 接口） | **换 pgvector**（PRD 决策 1），接口签名尽量保持一致 |
| 混合检索 + 重排 | `w6-rag/src/retriever.py`（BM25+向量 RRF）、`reranker.py` | 迁移 + 结构化过滤进 SQL |
| ReAct Runtime | `w8-agent-arch/src/react.py` | **核心复用**，两个专家 Agent 共用 |
| Plan-Execute | `w8-agent-arch/src/plan_execute.py` | 深度模式 orchestrator 用 |
| 记忆机制 | `w8-agent-arch/src/memory.py`（短期/长期） | 适配「搜索状态对象」结构化记忆 |
| MCP 接入 | `w8-agent-arch/src/mcp_server.py`、`mcp_tool_adapter.py` | 可选：把曲库工具包成 MCP server |
| 毕业项目骨架 | `w10-graduation/app/`（agent.py/api.py/main.py）、`tests/test_graduation.py`、`eval/evaluate.py` | FastAPI 结构参考 + 评估框架复用 |

## 迁移顺序建议

1. **W3 TokenBudget → LLM 抽象层**（M3 T-301）：所有 Agent 的地基
2. **W4 Tool 三件套 → 工具层**（M3 T-303）：曲库雷达工具集
3. **W5 RetryController → 打标管线**（M1 T-102）：DeepSeek 批量请求的稳定性保障
4. **W6 四件套 → RAG 底座**（M2）：chunker/embedder 保留，vector_store 换 pgvector
5. **W8 react.py → Agent Runtime**（M3 T-302）：两个专家 + 主 Agent 共用一个 Runtime，靠 system prompt + 工具集区分

## 迁移记录表

| 日期 | 模块 | 来源 | 调整说明 |
|---|---|---|---|
| — | — | — | — |

（每个迁移完成时填写，作为面试可讲的「演化史」素材）
