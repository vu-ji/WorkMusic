# W5 ai-trace

> AI 生成代码 → 人工 Review → 修改后的痕迹。

## retry_controller.py · 重试控制器

- 文件：`w5-error-retry/src/retry_controller.py`
- AI 生成：骨架（ErrorCategory / CircuitState 枚举 + RetryController 类签名 + TODO 注释）
- 人工 Review + 修改：
  - `categorize_error` 合并判断：`isinstance(exception, (asyncio.TimeoutError, ConnectionError, OSError, TimeoutError))`
  - 熔断器实现三态状态机：CLOSED → OPEN → HALF_OPEN
  - `is_circuit_open` 冷却期过期自动转 HALF_OPEN（探测模式）
  - 指数退避：`backoff_base * (2 ** attempt)`
  - 全量中文注释（前端类比：axios-retry / circuit breaker）

## test_retry.py · 测试

- AI 生成：3 个测试类骨架（错误分类 / 重试行为 / 熔断器），11 条用例 TODO
- 人工修改：补充到 14 条用例，覆盖：
  - 首次成功不重试
  - 前两次失败第三次成功（验证退避循环）
  - 重试耗尽返回 exhausted=True
  - 永久错误只调一次
  - 熔断阈值触发 / 阈值以下不触发 / 冷却后半开 / 半开后成功恢复

## 接入 Agent Loop（W4 代码改动）

- 文件：`w4-tool-use/src/agent.py`
- 改动：3 处
  - import 增加 `functools` + `RetryController` + w5 路径补丁
  - `__init__` 增加 `self.retry = RetryController(max_retries=3)`
  - 工具执行点：`functools.partial(self.executor.execute, action["tool"])` → `try_with_retry(exec_fn, arguments=...)`
- 验证：W4 24 条 + W5 14 条 = 38 tests 全绿

## mcp_sdk_trace.md · MCP SDK 精读

- 精读源码：`modelcontextprotocol/python-sdk`（用户路径 `/Users/vuji/workspace/github/python-sdk`）
- 追踪链路：call_tool → send_request → JSONRPCDispatcher.send_raw_request → Tool.run
- 产出：调用链路时序图 + 架构图 + MCP vs 手写 ToolRegistry 对比表 + 5 问答案
- 关键认知：`_pending[id]` 并发关联表 / MCPError vs ToolError 错误分层 / to_thread 线程池包装
