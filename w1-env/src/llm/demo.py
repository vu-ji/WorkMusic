# src/llm/demo.py —— W1 统一抽象层验证脚本
#
# 验证 RouterClient 的流式输出和性能指标。
# 两种模式：
#   默认（light）：uv run python -m src.llm.demo
#   推理（heavy）：ROUTER_DEFAULT_TIER=heavy uv run python -m src.llm.demo
#
# 输出指标：
#   - TTFT（Time To First Token）：首 token 延迟，衡量模型响应速度的关键指标
#   - 总耗时：从发请求到最后一个 token 接收完毕
#   - 输出字数：用于估算 token 消耗和成本
#
# 前端类比：这就像在浏览器控制台里 fetch + ReadableStream 逐字打印响应。
# TTFT 相当于第一个 chunk 到达的时间——SSE/流式场景下最关键的用户体验指标。

import asyncio
import time

from src.llm.router import RouterClient


async def main() -> None:
    """主函数：初始化 RouterClient，流式获取回复并打印性能指标"""
    # RouterClient 会自动读 ROUTER_DEFAULT_TIER 环境变量决定用哪个模型
    client = RouterClient()
    print(f"Model: {client.model_name}\n---")

    # time.monotonic() 返回单调递增时钟（不受系统时间调整影响），适合测量耗时
    start: float = time.monotonic()
    first_token: float | None = None  # 记录第一个 token 到达的时间戳
    total_chars: int = 0  # 统计输出总字数

    # 发起流式请求，逐 token 处理
    async for token in client.chat_stream(messages=[
        {"role": "user", "content": "我叫 vuji"},
        {"role": "assistant", "content": "你好, vuji"},
        {"role": "user", "content": "我叫什么"}
    ]):
        # 第一个 token 到达时，记录 TTFT（Time To First Token）
        if first_token is None:
            first_token = time.monotonic()
            # TTFT = 第一个 token 到达时间 - 请求发起时间
            ttft: float = first_token - start
            print(f"[首 token 延迟] {ttft:.2f}s\n---")

        # 逐字打印当前 token，flush=True 确保立即输出（不缓冲）
        print(token, end="", flush=True)
        total_chars += len(token)

    # 统计总耗时
    total: float = time.monotonic() - start
    print(f"\n---\n总耗时: {total:.2f}s | 输出字数: {total_chars}")
    if first_token:
        # 思考时间/预处理时间 = 第一个 token 到达的时间
        # 对于推理模型（r1），这包括模型加载 + 生成思考链的时间
        # 对于普通模型（qwen），这个时间很短（百毫秒级）
        thinking_time: float = first_token - start
        print(f"预处理/思考: {thinking_time:.2f}s")


if __name__ == "__main__":
    # asyncio.run() 是 Python 3.7+ 的标准异步入口
    # 相当于在 Node 里写 (async () => { await main() })()
    asyncio.run(main())
