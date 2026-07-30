# W5 · 错误重试 + MCP SDK 精读

W4 的 Agent Loop 在工具失败时把错误发给 LLM 修正——这是"语义级重试"。
W5 加"工程级重试"：在工具执行层面处理网络超时、临时故障，LLM 无感知。

## 目录

```
src/
├── retry_controller.py  # RetryController · 重试+退避+熔断
├── test_retry.py        # pytest 测试
└── mcp_sdk_trace.md     # MCP SDK 工具调用链路精读笔记
```

## 跑

```bash
make test
```

## 两种重试的分工

| | W4 Agent Loop | W5 RetryController |
|---|---|---|
| 处理什么 | 参数错误、业务逻辑错误 | 网络超时、连接失败、临时不可用 |
| 谁介入 | LLM（看到 error 后修正参数） | 系统自动重试，LLM 无知 |
| 重试次数 | 受 MAX_TURNS 限制（3 轮） | 独立 count（可设 3-5 次） |
| 前端类比 | 表单校验 400 → 用户修 | Axios-retry 5xx → 自动重试 |
