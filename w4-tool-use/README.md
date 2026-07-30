# W4 · Tool Use / Function Calling

手写 Agent Loop（think → act → observe），不依赖任何框架。给模型工具而不是 prompt 约束——这是 W2 "怎么让模型不编造"的代码级答案。

## 目录

```
src/
├── tool_schema.py    # JSON Schema 定义 + search_catalog mock + TOOLS 字典
├── tool_registry.py  # ToolRegistry · 注册/查找/schema 导出
├── tool_executor.py  # ToolExecutor · 执行+参数校验+错误格式化（兼容 sync/async）
├── agent.py          # Agent Loop · think → act → observe 循环
├── test_tool.py      # pytest 24 条（注册表/执行/校验/解析容错）
└── test_agent.py     # e2e 全链路（3 个用例，需 ollama 运行）
```

## 跑

```bash
make test         # pytest 24 条
make run-e2e      # 全链路 e2e（需 ollama 在跑）
```

## Agent Loop 架构

```
用户提问 → LLM 决策（调工具 or 回复）
              ↓ 调工具
         Executor 执行 → 结果/错误
              ↓
         追加到消息历史 → 再问 LLM
              ↓ 回复
         返回最终文本
```

最多 3 轮，防止死循环。tool_executor 用 `inspect.iscoroutinefunction` 兼容同步和异步工具，W6 接真实数据库时 zero change。

## e2e 结果

| 用例 | 轮次 | 工具调用 | 行为 |
|---|---|---|---|
| 检索曲库（电子摇滚 BPM 130-150） | 2 | 1 | 调 search_catalog → 拿到 2 首匹配 → 自然语言回复 |
| 打招呼 | 1 | 0 | 直接 reply |
| 预算过低无匹配 | 2 | 1 | 调 search_catalog → 空列表 → 告知用户无匹配 |

## W2 vs W4

W2：prompt 说"禁止编造" → 模型找 loophole，加免责声明后继续编。
W4：模型只能调 `search_catalog` → 函数返回什么说什么，函数返回空就说无数据。
