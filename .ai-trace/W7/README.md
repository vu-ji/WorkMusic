# W7 ai-trace

> AI 生成代码 → 人工 Review → 修改后的痕迹。

## reranker.py · LLM 重排序（W7 实现）

- AI 生成：完整 LLMReranker 实现（逐条打分 + 容错解析 + 分数归一化）
- 设计决策：
  - 方案 B（LLM 打分）替代方案 A（bge-reranker）——Ollama 无 rerank 模型，零新依赖
  - 逐条打分替代批量排序——可解释、单条失败不影响其他、分数可比
  - temperature=0.0——打分要确定性，避免随机分数
  - 分数归一化——LLM 可能输出 0-1 或 0-100，统一到 0-10
- 复用：RouterClient（W1）路径补丁 + chat_sync

### 重构：两层重试拆开，复用 W5 RetryController（人工 Review 发现）

- 问题：初版 `_score_one` 用 try/except 把所有重试混在一起——网络错误和解析失败无法区分，且未复用 W5 的 RetryController
- 修改：
  - 网络层：LLM 调用包进 `self.retry.try_with_retry(call_llm)`——瞬时错误自动退避，重试耗尽返回 success=False
  - 语义层：`_parse_score` 解析失败 → 重新生成一轮（LLM 输出格式问题，非网络问题）
  - `__init__` 增加 `self.retry = RetryController(max_retries=2)`
- 验证：20 passed 全绿（含真实 LLM 重排）
- 收获：**组件跨周复用首次出现（W5 → W7）**——面试可讲"两层重试职责分离 + 组件复用"

## test_rag.py · 新增 5 条测试

- parse_score：纯 JSON / markdown 剥离 / 归一化 / 非法输入
- rerank_reorders：真实 LLM 重排验证
- 结果：20 passed（原 15 + 新 5）

## test_rag_e2e.py · 完整管线

- 6 条文档入库 → 3 个 query → 检索（RRF）→ 重排（LLM）→ top1 对比
- 结论：top1 全稳定（检索质量高时重排不改判），但重排拉开分数、压噪声候选
