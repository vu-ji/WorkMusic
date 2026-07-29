# W3 · 上下文管理与成本控制

TokenBudget 预算系统，接入 RouterClient 全链路验证。

## 目录

```
src/
├── token_budget.py  # TokenBudget · count / is_within_budget / trim
├── test_budget.py   # pytest 6 用例
└── test_e2e.py      # 全链路：超长对话 → trim → 模型调用 → 成本
```

## 跑

```bash
make test         # pytest 6 用例
make run          # 快速验证（手跑模式，已废弃）
make run-e2e      # 全链路 e2e
```

## TokenBudget 设计

| 方法 | 职责 | 关键决策 |
|---|---|---|
| `count(messages)` | tiktoken json.dumps 全量序列化计数 | 从 /4 估算迭代到精确方案 |
| `is_within_budget(messages, max_output)` | 预算判断，预留输出空间 | 返回 `(bool, current, remaining)` |
| `trim(messages, max_tokens)` | 保留 system + 从新到旧保留 | system 超预算时静默返回 |

## e2e 验证

```
[TokenBudget] input=143953 | trimmed_to=101538 | saved=42415
usage: prompt=101538 completion=31 cost=¥0.203324
```

80 轮假对话从 143K token 裁到 101K，全链路跑通。
