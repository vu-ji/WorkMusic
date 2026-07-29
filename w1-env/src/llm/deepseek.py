import os
from pathlib import Path
from typing import override
from collections.abc import AsyncGenerator

from dotenv import load_dotenv
from openai import AsyncOpenAI, AsyncStream
from openai.types.chat import ChatCompletionChunk, ChatCompletionMessageParam

from .provider import LLMProvider

# 加载项目根目录的 .env（w1-env/.env），让 DEEPSEEK_API_KEY 等在任何运行目录下都生效
_ = load_dotenv(Path(__file__).parent.parent.parent / ".env")


class DeepseekProvider(LLMProvider):
    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        """初始化 Deepseek provider

        Args:
            model: deepseek 模型名，如 "deepseek-v4-flash"、"deepseek-v4-pro"
                  不传则读 DEEPSEEK_MODEL 环境变量，再没有就默认 deepseek-v4-flash
            base_url: deepseek 服务的完整 URL（OpenAI 兼容，不用带 /v1 后缀）
                     不传则读 DEEPSEEK_BASE_URL 环境变量，再没有默认 https://api.deepseek.com
            api_key: DeepSeek API Key；不传则读 DEEPSEEK_API_KEY 环境变量
        """
        self._model: str = model or os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
        base_url = base_url or os.getenv(
            "DEEPSEEK_BASE_URL", "https://api.deepseek.com"
        )

        # DeepSeek 云端强制校验真实 API Key（与本地 ollama 不同）。
        # 优先用构造参数，其次 DEEPSEEK_API_KEY 环境变量；都没有就明确报错。
        api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError(
                "缺少 DeepSeek API Key：请设置 DEEPSEEK_API_KEY 环境变量，或在构造 DeepseekProvider 时传入 api_key="
            )

        # 把真实 key 传给 SDK（不再借用 OPENAI_API_KEY 占位）
        self._client: AsyncOpenAI = AsyncOpenAI(base_url=base_url, api_key=api_key)

    @property
    @override
    def model_name(self) -> str:
        """返回当前加载的模型名称"""
        return self._model

    @override
    async def chat_stream(
        self, messages: list[ChatCompletionMessageParam], temperature: float = 0.8
    ) -> AsyncGenerator[str, None]:
        """调用 deepseek 流式接口，逐 token yield 响应文本

        流式请求流程（类比前端 fetch + ReadableStream）：
        1. create(stream=True) → 发起请求，拿到 AsyncStream（类似 Response.body）
        2. async for chunk in stream → 遍历每个数据块（类似 reader.read() 循环）
        3. chunk.choices[0].delta.content → 每个块可能带一个 token（类似 stream chunk 的 value）
        4. yield content → 吐出给调用方（RouterClient → demo.py 打印到终端）

        Args:
            messages: OpenAI 格式消息列表

        Yields:
            每个文本 token。None 或空字符串被跳过（流式响应的最后一个 chunk 可能 content 为 None）
        """
        # 发起流式聊天请求，stream=True 是关键——让 API 返回事件流而非完整响应
        stream: AsyncStream[ChatCompletionChunk] = (
            await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                stream=True,  # 启用流式：逐 token 返回，不等人话说完
                temperature=temperature
            )
        )

        # 逐块消费流式响应
        # 每个 chunk 的结构：{"choices": [{"delta": {"content": "你"}, "index": 0}]}
        # 最后一个 chunk 的 delta.content 通常为 None，用 if content 过滤掉
        async for chunk in stream:
            # 取当前块中的文本增量——可能为 None（流结束信号）
            content: str | None = chunk.choices[0].delta.content
            if content:  # 过滤 None 和空字符串
                yield content  # 吐出这个 token，让上游逐字处理
