# 开发规范（Conventions）

> 所有 Agent 生成的代码必须遵守。违反即打回重写。

## 语言与栈

- **后端**：Python 3.12+，FastAPI，类型注解（mypy 友好）
- **前端**：TypeScript（strict），React 18 + Vite
- **模型**：优先国内可调用（DeepSeek / 通义 / Ollama），统一 OpenAI 兼容协议

## 目录结构

```
backend/
  app/                 # 应用主代码
    agents/            # 专家 Agent（curator 曲库雷达 / sentinel 合同哨兵 / orchestrator）
    rag/               # 检索（retriever/reranker/embedder）
    llm/               # LLM 抽象层（providers/router/budget）
    tools/             # 工具注册与执行（复用 W4）
    workspace/         # blackboard 工作区上下文
    api/               # FastAPI 路由（SSE）
    observability/     # 观测（tokens/成本/延迟）
  data_pipeline/       # M1 数据管线（clean/tag/synthesize/ingest）
  data/                # raw/ clean/ tagged/（gitignore）
  tests/               # pytest
frontend/
  src/                 # React 工作台
docs/                  # 本仓库规格层
```

## 代码标准

- 中文注释/文档，技术名词保留英文（context window、grounding、blackboard）
- 命名：Python `snake_case`，TS `camelCase`；模块文件小写
- 每个模块必须有最小测试（pytest，命名 `test_*.py`）
- 禁止魔法数裸奔；配置进 `.env.example` + 环境变量
- 敏感操作（生成合同/报价）必须有 human-in-the-loop 确认点

## 测试

```bash
cd backend && python -m pytest          # 全量
cd backend && python -m pytest tests/test_xxx.py -k keyword
```

- 测试是验收标准的一部分：任务验收标准列了什么，就要有什么测试
- e2e 级测试：Agent 全流程（找歌→追问→报价）要有至少 1 条

## Commit 规范

- 格式：`<type>(<scope>): <description>`
- type：`feat | fix | refactor | docs | chore | test`
- scope：`data-pipeline | rag | agent-runtime | ui | workspace | obs | contract | eval | infra`
- 示例：`feat(rag): pgvector 混合检索接入 search_catalog`

## 文档要求

- 每个里程碑结束：`docs/milestones.md` 勾选 + 阻塞登记清空
- 踩坑必记：`docs/pitfalls.md`（现象 → 根因 → 解法 → 举一反三）
- README 必须声明：数据来源（ChineseLyrics）、版权立场、本地运行方式

## 版权红线（重复强调）

- 对外部署版歌词只展示 ≤2 句片段；接口不返回完整歌词
- 数据文件（raw/clean/tagged）不提交 git（走 gitignore）
