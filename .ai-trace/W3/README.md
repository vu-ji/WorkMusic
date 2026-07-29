# W3 ai-trace

> 记录 AI 生成代码 → 人工 Review → 修改后的痕迹。

## TokenBudget · token 预算管理

- 文件：`w3-context/src/token_budget.py`
- AI 生成：类框架（`__init__` / `count` / `is_within_budget` / `trim` 方法签名）
- 人工 Review + 修改：四轮迭代，每轮修复一个关键 bug

**迭代记录：**

| 轮次 | 问题 | 根因 | 修复 |
|---|---|---|---|
| 1 | `count()` 除数 `/2` | 中文严重低估 | 改 `/4` |
| 2 | `is_within_budget` 返回 `self.model_window - tokens` | 剩余额度应基于 budget 而非 model_window | 改 `self.budget - tokens` |
| 3 | `is_within_budget` 返回元组当 Boolean 用 | Python 非空元组为 truthy | 解构 `ok, _, _ = ...` |
| 4 | `trim` 追加后检查 `if count > budget: break` | 多一条才停 | 改追加前累加判断 |
| 5 | `trim` 追加前检查 `if count(result) > budget` | 检查的是追加前总量 | 改 `count(result) + count([msg]) > budget` |
| 6 | `get_safe_message` 误声明 `async def` | 内部无 await | 改 `def` |
| 7 | `count` 无防御 content 缺失 | 消息可能无 content 字段 | 改 `message.get("content", "")` |
| 8 | `sefl` 拼写错误 | 手误 | 改 `self` |

**最终方案**：`TokenBudget` 四轮 code review 后定型。接入 tiktoken 后从 /4 估算升级到 `json.dumps(messages)` 全量序列化计数，误差从 40% 降到 1.3%。

## RouterClient 集成 TokenBudget

- 文件：`w1-env/src/llm/router.py`
- AI 生成：无（完全人工手写）
- 人工实现：`get_safe_message()` 预算检查、`chat_sync` 加入 usage 零值检测 fallback、TokenBudget 日志输出

## Ollama usage=0 发现

- 现象：`CompletionUsage(completion_tokens=0, prompt_tokens=0, total_tokens=0)`
- 排查：在 `RouterClient.chat_sync` 加 `print("[DEBUG] usage raw:", response.usage)` 确认结构体存在但字段全零
- 解法：零值检测 → `type(usage)(...)` 重建 usage 对象，fallback 到字符估算

## e2e 验证

- 文件：`w3-context/src/test_e2e.py`
- AI 生成：骨架（路径补丁 + PromptManager 加载 + 构造超长对话 + 成本输出）
- 人工修改：填入具体调用逻辑、trim 裁剪验证、`estimate_cost` 成本输出
- 验证结果：143953 → 101538 token，成本 ¥0.20
