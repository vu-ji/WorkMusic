# W10-11 毕业项目（Phase 5）

个人知识库问答 Agent（A）+ Dify 插件（B），借助开源框架完成。

## 架构（A：主项目）

```
app/
├── main.py          # CLI 入口（W11 加 FastAPI）
├── agent.py         # ReAct 决策层（W8 升级：多工具 + 记忆 + 状态）
├── tools/           # 工具注册层
│   └── __init__.py  # search_catalog + knowledge_search
└── memory/          # 记忆层（W8 封装）
    └── __init__.py
```

### 组件复用清单

| 组件 | 来源 | 用途 |
|---|---|---|
| RouterClient | W1 | LLM 调用（middle=qwen2.5:14b）|
| TokenBudget | W3 | 上下文裁剪 |
| ToolExecutor/search_catalog | W4 | 曲库检索 |
| RetryController | W5 | 工具执行重试 |
| RAG 管线（chunker/embedder/vector_store/retriever/reranker）| W6/W7 | 知识检索 |
| ReAct / Plan-Execute | W8 | 决策范式 |
| ShortTermMemory / LongTermMemory | W8 | 多轮 + 跨会话记忆 |
| MCP server/adapter | W8 | 工具协议层 |

### 借鉴开源设计

| 开源 | 借鉴点 |
|---|---|
| LangGraph | 状态机思想：state 在节点间流转 |
| graphon (Dify) | 工具注册 = 节点注册表，引擎不认识工具 |
| ComfyUI | 强类型工具输入（参数 schema 校验）|

## B：Dify 插件

把 W5 的 RetryController 做成 Dify 插件工具（RetryTool），用官方插件 SDK。

```
dify-plugin-retry/
├── provider/        # 插件声明
├── tools/           # RetryTool（复用 W5 逻辑）
└── plugin.yaml
```

## 里程碑

- W10：架构 + 骨架（agent/tools/memory）+ Dify 插件骨架
- W11：核心功能（多工具 + RAG 接入 + 记忆）+ 插件实现
- W12：评估（20+ query 批量跑）+ 博客 12/6 + 收尾
