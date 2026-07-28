"""W3 e2e: TokenBudget → RouterClient → 真实模型调用 → 成本日志"""

import asyncio
import sys
from pathlib import Path

# 1. 路径 —— 你已经有 w1-env 和 w2-prompts 的路径补丁模式，照搬
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "w2-prompts" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "w1-env"))

from prompt_manager import PromptManager        # w2
from token_counter import estimate_cost          # w2
from src.llm.router import RouterClient           # w1

pm = PromptManager(Path(__file__).parent.parent.parent / "w2-prompts" / "prompts" / "catalog_radar")

def make_oversized_messages(system_prompt: str, rounds: int = 80) -> list[dict]:
    """构造超长对话：system + N 轮假对话，触发 trim"""
    messages = [{"role": "system", "content": system_prompt}]
    for i in range(rounds):
        messages.append({"role": "user", "content": f"第{i}轮用户问题：{'X' * 10000}"})
        messages.append({"role": "assistant", "content": f"第{i}轮助手回复：{'Y' * 2000}"})
    return messages


async def main():
    # 2. 加载 system prompt
    # TODO: 用 PromptManager 加载 catalog_radar/v1_fewshot
    vars = {"agent_name": "小曲", "agent_title": "曲库雷达", "max_candidates": 10}
    version = "v1_fewshot"
    system_prompt = pm.load(version, **vars)

    # 3. 构造超长消息
    # TODO: 调 make_oversized_messages
    messages = make_oversized_messages(system_prompt)

    # 4. 创建 client + 检查裁剪前后 token 数
    # TODO: RouterClient("light")
    # TODO: client.budget.count(messages) 裁前
    # TODO: client.get_safe_message(messages) 裁后
    # TODO: print("[TokenBudget] input=... | trimmed_to=... | saved=...")
    client = RouterClient()
    # print(f"[TokenBudget] input={client.budget.count(messages)} | trimmed_to={client.budget.count(client.get_safe_message(messages))} | saved=")

    # 5. 非流式调用 + 成本
    # TODO: reply, usage = await client.chat_sync(...)
    # TODO: estimate_cost(usage.prompt_tokens, usage.completion_tokens, "light")
    # TODO: print("usage: prompt=... completion=... cost=¥...")
    reply, usage = await client.chat_sync(messages)
    
    print(f"usage: prompt={usage.prompt_tokens} completion={usage.completion_tokens} cost=¥{estimate_cost(usage.prompt_tokens, usage.completion_tokens, 'light')}")

    # 6. 打印模型回复摘要（前 200 字）
    # TODO: print(reply[:200])
    print(reply[:200])


if __name__ == "__main__":
    asyncio.run(main())
