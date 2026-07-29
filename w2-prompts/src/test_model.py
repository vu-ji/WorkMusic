"""Prompt A/B 对比：v0 vs v1_fewshot"""
from pathlib import Path
import asyncio
import sys
sys.path.insert(0, str(Path(__file__).parent))  # 把自己的 src/ 加进去
from prompt_manager import PromptManager

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "w1-env"))            # 确认已插入

from src.llm.router import RouterClient


agent = Path("prompts/catalog_radar")
pm = PromptManager(agent)
vars = {"agent_name": "小曲", "agent_title": "曲库雷达", "max_candidates": 10}

v0 = pm.load("v0", **vars)
v1 = pm.load("v1_fewshot", **vars)

query = "给连锁健身房找 10 首 bgm，电子/摇滚，BPM 130–150，纯器乐，预算每年 5 万"

async def run(prompt_name, system_prompt, tier: str = ''):
    print(f"\n{'='*60}")
    print(f"  {prompt_name}")
    print(f"{'='*60}")
    client = RouterClient(tier=tier)  # 👈 你可能需要传 tier 参数
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query},
    ]
    async for token in client.chat_stream(messages):
        print(token, end="", flush=True)
    print()

async def main():
    await run("v0", v1, tier='light')
    await run("v1", v1, tier='middle')
    # await run("v0", v0, tier='heavy')
    # await run("v1_fewshot", v1)

asyncio.run(main())
