# W1 ai-trace

> 记录 AI 生成代码 → 人工 Review → 修改后的痕迹。面试证据链：对应「带代码 30 分钟 review 最棘手的 Agent 工程问题」。

## RouterClient · 模型路由客户端

- 文件：`src/llm/router.py`
- AI 生成：整体类结构、ROUTER_CONFIG 字典、chat_stream 委托模式
- 人工 Review：Python 抽象基类用 ABC 而非 Protocol 的设计决策（审查后确认 ABC 更适合 provider 这种"缺方法就不可用"的场景）
- 人工修改：添加完整中文注释（前端类比 Axios interceptor）、添加类型标注 `ChatCompletionMessageParam`
- 后续 W3 集成：`get_safe_message()` 接入 TokenBudget（人工手写），`chat_sync` 加入 usage 零值检测 fallback（人工手写）

## OllamaProvider · 流式调用

- 文件：`src/llm/ollama.py`
- AI 生成：AsyncOpenAI 客户端初始化、chat_stream 流式循环、chat_sync 非流式封装
- 人工 Review：确认 `stream=True` 参数位置、`response_format={"type":"json_object"}` 对 JSON 输出的影响
- 人工修改：添加中文注释标注流式流程（类比 fetch + ReadableStream）、添加 dotenv 加载逻辑

## LLMProvider · 抽象基类

- 文件：`src/llm/provider.py`
- AI 生成：ABC 抽象基类定义、@abstractmethod 装饰器
- 人工 Review：异步生成器的抽象方法声明陷阱——base class 用 def（非 async def），子类用 async def + yield（pyright 兼容性）
- 人工修改：添加大段注释解释这个坑，前端类比 interface LLMProvider

## FastAPI SSE 端点

- 文件：`src/api/chat.py`
- AI 生成：FastAPI app 初始化、SSE StreamingResponse 流式端点
- 人工修改：接入 RouterClient、逐 token 推送 `data: xxx\n\n`

## demo.py · TTFT 性能验证

- 文件：`src/llm/demo.py`
- AI 生成：流式验证脚本框架
- 人工修改：添加 `time.monotonic()` 计时逻辑、TTFT 首 token 延迟计算
- 实测数据：qwen2.5:7b TTFT ≈ 1.2s，deepseek-r1:32b TTFT ≈ 14s（含 CoT）
