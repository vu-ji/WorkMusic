# src/llm/router.py —— 路由客户端：按 tier 自动选择模型
#
# RouterClient 是 W1 统一抽象层的核心对外接口。
# 外部代码只需要 new RouterClient()，不需要关心背后是哪个模型厂商。
# 对应  职责②：「多厂商 LLM 统一抽象层 + 模型路由」
#
# 当前实现：按 tier（light/heavy）选择不同 ollama 模型
# 后续演进（W4/W8 逐步加）：
#   light → ollama qwen2.5:7b（快速日常）
#   heavy → ollama deepseek-r1:32b（深度推理）
#   cloud → DeepSeek/Qwen 云端 API（质量兜底，fallback）
#
# 前端类比：类似 Axios 实例 + baseURL 切换拦截器——调用方只调 .get()，
# 背后是走内网还是公网、哪台服务器，由 Router 决定。

import os
from collections.abc import AsyncGenerator

from openai.types.chat import ChatCompletionMessageParam

from src.llm.ollama import OllamaProvider
from src.llm.provider import LLMProvider


class RouterClient:
    """模型路由客户端

    根据 tier 配置自动选择 LLM provider。
    对外暴露统一的 chat_stream 接口，调用方无需感知底层模型差异。

    用法：
        client = RouterClient("light")          # 默认 7b 模型
        client = RouterClient("heavy")          # 32b 推理模型
        async for token in client.chat_stream([{"role": "user", "content": "你好"}]):
            print(token)
    """

    _provider: LLMProvider  # 实际提供流式能力的底层 provider 实例

    def __init__(self, tier: str | None = None):
        """初始化路由客户端

        路由策略（硬编码，后续可扩展为配置文件驱动）：
        - "light" → qwen2.5:7b（轻量快速，适合日常对话和简单检索）
        - "heavy" → deepseek-r1:32b（深度推理，适合复杂规划和合同审查）

        Args:
            tier: 模型等级，可选 "light" / "heavy" / "deepseek"
                  不传则读 ROUTER_DEFAULT_TIER 环境变量
                  再没有默认 "light"
        """
        tier = tier or os.getenv("ROUTER_DEFAULT_TIER", "light")
        print(f"tier: {tier}")
        if tier == "light":
            self._provider = OllamaProvider("qwen2.5:7b")
        elif tier == "heavy":
            self._provider = OllamaProvider("deepseek-r1:32b")
        elif tier == "deepseek":
            self._provider = OllamaProvider("deepseek-v4-flash")
        else:
            raise ValueError(f"未知 tier: {tier}，可选值: light, heavy")

    @property
    def model_name(self) -> str:
        """获取当前路由选中的模型名称，用于日志/观测面板展示"""
        return self._provider.model_name

    async def chat_stream(
        self, messages: list[ChatCompletionMessageParam]
    ) -> AsyncGenerator[str, None]:
        """统一的流式聊天接口

        完全委托给当前选中的 provider，自身只做路由不做任何处理。
        保持接口透明——调用方不需要知道 token 是来自本地模型还是云端。

        Args:
            messages: OpenAI 格式消息列表

        Yields:
            逐 token 文本，委托自底层 provider 的 chat_stream
        """
        stream: AsyncGenerator[str, None] = self._provider.chat_stream(messages)
        async for token in stream:
            yield token
