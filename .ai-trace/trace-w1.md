# trace-001 · OllamaProvider 流式实现

- 日期：2026-07-26
- AI 生成内容：OllamaProvider.chat_stream() 初版（见 commit a1b2c3）
- 我 review 发现的问题：
  1. 没有处理 stream 中断的异常
  2. AsyncOpenAI 的 base_url 需要以 /v1 结尾（AI 漏了）
  3. content 为 None 时没有跳过（某些 chunk 只有 metadata）
- 我做的修改：
  1. 加了 try/finally 确保连接关闭
  2. base_url 补了 /v1
  3. 加了 `if content is None: continue`
- 学到什么：openai SDK 的 stream chunk 不一定每个都有 content，production 代码必须判空
