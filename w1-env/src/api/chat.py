# src/api/chat.py —— FastAPI SSE 聊天端点
#
# 通过 HTTP SSE（Server-Sent Events）暴露流式聊天能力。
# 这是 WorkMusic 前端流式对话的后端原型——W11 时前端就是连这个端点。
#
# SSE 原理（前端类比）：
# 普通 API：请求 → 等待完整响应 → 返回 JSON（类似 fetch + Response.json()）
# SSE 请求：请求 → 建立长连接 → 逐行推送 "data: xxx\n\n"（类似 EventSource / fetch + ReadableStream）
#
# uvicorn 前置条件：
# pip install fastapi uvicorn 已在 W1 环境装好
# 启动命令：uv run uvicorn src.api.chat:app --reload --port 8000
# 测试：浏览器访问 http://localhost:8000/chat?msg=你好

from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from src.llm.router import RouterClient  # noqa: E402 — 忽略 import 顺序检查

# 创建 FastAPI 应用实例
# FastAPI 自动生成 OpenAPI 文档，访问 http://localhost:8000/docs 可交互测试
app: FastAPI = FastAPI(title="WorkMusic Chat API", version="0.1.0")

# 全局 RouterClient 实例（目前跑 light 模型，后续可在初始化时根据配置选 tier）
client: RouterClient = RouterClient()


@app.get("/chat")
async def chat(msg: str) -> StreamingResponse:
    """SSE 流式聊天端点

    Args:
        msg: 用户输入的文本，通过 URL 查询参数传入
             示例：GET /chat?msg=你好

    Returns:
        StreamingResponse —— FastAPI 内置的流式响应对象
        设置 media_type="text/event-stream" 告诉浏览器这是一个 SSE 连接

    响应格式（SSE 协议）：
        data: 第\n\n
        data: 一个\n\n
        data: token\n\n
        ...

    前端接收（JavaScript）：
        const evtSource = new EventSource("/chat?msg=你好")
        evtSource.onmessage = (event) => console.log(event.data)
    """

    async def generate() -> AsyncGenerator[bytes, None]:
        """内部生成器：从 RouterClient 获取流式 token，包装为 SSE 格式

        SSE 协议规定每行数据以 "data: " 开头，以 "\n\n" 结尾。
        前端 EventSource 自动解析这个格式，每次收到 "\n\n" 触发一次 onmessage。

        Yields:
            bytes 格式的 SSE 事件数据，Uvicorn 通过 HTTP 长连接推送
        """
        # messages 准备：构建 OpenAI 格式的消息列表
        # 这是 chat_stream 的标准输入格式，所有 provider 共享
        messages = [{"role": "user", "content": msg}]

        # 从 RouterClient 获取流式 token，实时推送给前端
        async for token in client.chat_stream(messages):
            # SSE 格式："data: <内容>\n\n"
            # encode("utf-8") 将字符串转为字节，因为 StreamingResponse 需要 bytes
            yield f"data: {token}\n\n".encode("utf-8")

    # StreamingResponse 接收一个 async generator，FastAPI 自动处理
    # HTTP 头部：Content-Type: text/event-stream → 前端 EventSource 识别
    # 前端收到后解析 data: 行，提取 token 逐个渲染
    return StreamingResponse(generate(), media_type="text/event-stream")
