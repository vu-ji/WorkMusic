# src/llm/provider.py —— 模型提供者抽象基类
#
# 定义所有 LLM provider 必须遵守的接口契约。
# 新加一个 provider（比如 DeepSeek 云端），只需继承 LLMProvider 实现 chat_stream 和 model_name。
# 类似 TypeScript 的 abstract class：约束子类结构，保证 RouterClient 不用改代码就能换模型。

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

from openai.types.chat import ChatCompletionMessageParam


class LLMProvider(ABC):
    """模型提供者抽象基类

    所有 provider 必须实现：
    - model_name（property）：返回当前模型名称，用于日志/观测面板
    - chat_stream()：接收消息列表，逐步 yield 文本 token

    前端类比：interface LLMProvider { model_name: string; chat_stream(messages): AsyncGenerator<string> }
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """返回当前模型名称（如 "qwen2.5:7b"），用于日志和观测面板标识"""
        ...

    @abstractmethod
    async def chat_stream(
        self, messages: list[ChatCompletionMessageParam]
    ) -> AsyncGenerator[str, None]:
        """接收消息列表，逐 token yield 文本

        Args:
            messages: OpenAI 格式的消息列表
                [{"role": "user", "content": "你好"}]
                role 可以是 "system"、"user"、"assistant"

        Yields:
            每个文本 token（字符串）
            注意：None/空 token 已被过滤，调用方不会收到空内容

        ⚠️ 抽象异步生成器的坑：
        基类用 def（不是 async def）声明，因为 Python 的 async def + yield 组合
        会让类型检查器（pyright）误以为返回 Coroutine 而不是 AsyncGenerator。
        子类实现时用 async def + yield，返回类型实际是 AsyncGenerator，pyright 能正确识别。
        """
        # yield "" 是空桩，让抽象方法有合法的语法体。
        # 子类必须 override，这个 yield 永远不会被执行到。
        # 不能用 pass，因为抽象生成器方法必须有 yield 语句才能通过语法检查。
        yield ""
