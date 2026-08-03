# W10 ai-trace

> AI 生成代码 → 人工 Review → 修改后的痕迹。

## 毕业项目 A：个人知识库问答 Agent

- AI 生成：架构（agent/tools/memory/main/api/eval/tests）+ 全部实现
- 关键设计：
  - ReAct 决策层升级：多工具注册 + 短期/长期记忆注入 + W5 重试
  - 工具接口约定：handler(arguments) → {"success", "result"/"error"}（同步/异步兼容）
  - 长期偏好用 LLM 抽取（PREFERENCE_PROMPT），失败静默降级
  - FastAPI：/chat（session 隔离）+ /health + /memory CRUD
- 踩坑修复：
  - `from memory import` 解析到 W8 的 memory.py（模块名冲突）→ 包前缀 `from app.memory import`
  - `_safe_call` 对 handler 返回裸 list 会 `.get()` 报错 → isinstance 判断包一层
  - 偏好提取原实现里 `asyncio.run` 嵌套问题 → 拆成 `_run_pref_extraction`

## 毕业项目 B：Dify 插件 RetryTool

- AI 生成：plugin.yaml + provider yaml + tools yaml + provider/retry.py + 逻辑层
- 发现：Dify 插件 SDK 包名是 `dify-plugin`（PyPI），不是 dify-plugin-sdk
- 踩坑：`Tool.__init__` 需要 runtime/session（Dify 运行时注入）→ 逻辑层独立测
- 踩坑：RetryController 内部 await fn()，sync lambda 报 "dict can't be awaited" → async def
- 状态：SDK 壳可加载 + 逻辑层 3 用例全过；平台打包部署留待 W11

## 评估脚本

- eval/evaluate.py：22 query 批量跑，统计成功率/平均轮次/工具命中/失败明细
