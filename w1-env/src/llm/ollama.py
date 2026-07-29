# src/llm/ollama.py —— Ollama 本地模型 provider
#
# 通过 OpenAI 兼容协议（/v1/chat/completions）调用本机 ollama 服务。
# Ollama 的 API 设计和 OpenAI 完全一致，所以直接用 AsyncOpenAI SDK。
# 只需要改 base_url 指向本地端口，api_key 填占位符（ollama 不校验）。
#
# 前端类比：这就像 axios baseURL 从 https://api.openai.com 改成 http://localhost:11434/v1，
# 其他请求体/响应结构完全不变。

import os
from pathlib import Path
from collections.abc import AsyncGenerator
from typing import override

from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai._streaming import AsyncStream
from openai.types.chat import ChatCompletionMessageParam
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk

from src.llm.provider import LLMProvider

# 加载项目根目录的 .env（w1-env/.env），让 OLLAMA_* 等配置在任何运行目录下都生效
_ = load_dotenv(Path(__file__).parent.parent.parent / ".env")


class OllamaProvider(LLMProvider):
    """Ollama 本地模型 provider

    通过 OpenAI 兼容协议调用本地 ollama 服务。
    支持所有 ollama pull 下来的模型（qwen2.5:7b / deepseek-r1:32b 等）。

    主要配置项（通过环境变量或构造参数传入）：
    - OLLAMA_MODEL：要用的模型名，默认 qwen2.5:7b
    - OLLAMA_BASE_URL：ollama 服务的地址，默认 http://127.0.0.1:11434/v1
    """

    def __init__(self, model: str | None = None, base_url: str | None = None):
        """初始化 Ollama provider

        Args:
            model: ollama 模型名，如 "qwen2.5:7b"、"deepseek-r1:32b"
                  不传则读 OLLAMA_MODEL 环境变量，再没有就默认 qwen2.5:7b
            base_url: ollama 服务的完整 URL（带 /v1 后缀）
                     不传则读 OLLAMA_BASE_URL 环境变量，再没有默认 http://127.0.0.1:11434/v1
        """
        self._model: str = model or os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        base_url = base_url or os.getenv(
            "OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1"
        )

        print("model:", self._model)

        # ⚠️ 新版 openai SDK 强制要求 api_key 或 OPENAI_API_KEY 环境变量。
        # ollama 不校验 key 内容，设个占位让 SDK 不报错。
        # 用 setdefault：后续如果设了真实云端的 key，不会被覆盖。
        _ = os.environ.setdefault("OPENAI_API_KEY", "ollama")

        self._client: AsyncOpenAI = AsyncOpenAI(base_url=base_url)

    @property
    @override
    def model_name(self) -> str:
        """返回当前加载的模型名称"""
        return self._model

    async def chat_sync(self, messages: list[ChatCompletionMessageParam], temperature: float = 0.8):
        """非流式调用，只为拿 usage"""
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
        )
        print("[DEBUG] usage raw:", response.usage)
        return response.choices[0].message.content, response.usage

    @override
    async def chat_stream(
        self, messages: list[ChatCompletionMessageParam], temperature: float = 0.8
    ) -> AsyncGenerator[str, None]:
        """调用 ollama 流式接口，逐 token yield 响应文本

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
                temperature=temperature,
                response_format={ "type": "json_object" },
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
