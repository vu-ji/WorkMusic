# W1 · 环境与认知校准

WorkMusic 项目的 LLM 基础设施。local-first 三层路由：light(7b) / middle(8b) / heavy(32b) / cloud(deepseek-chat)。

## 目录

```
src/llm/
├── provider.py   # LLMProvider ABC 抽象基类
├── ollama.py     # Ollama OpenAI 兼容协议适配器
├── deepseek.py   # DeepSeek 云端 API 适配器
├── router.py     # RouterClient · 三层路由 + TokenBudget 集成
└── demo.py       # 流式验证 + TTFT 性能测试
src/api/
└── chat.py       # FastAPI SSE 流式端点
```

## 跑

```bash
# 流式验证（打印 TTFT）
make run          # light tier (qwen2.5:7b)
ROUTER_DEFAULT_TIER=heavy make run   # heavy tier (r1:32b)

# SSE 端点
uvicorn src.api.chat:app --reload
curl -N http://localhost:8000/chat -d '{"query":"你好"}'
```

## 性能数据

| 模型 | TTFT | 说明 |
|---|---|---|
| qwen2.5:7b | ~1.2s | 适合高频简单查询 |
| deepseek-r1:32b | ~14s | 含 CoT 思考链，适合深度推理 |
