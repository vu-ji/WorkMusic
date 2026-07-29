
import asyncio
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent))  # 把自己的 src/ 加进去
from prompt_render import load_prompt
from prompt_manager import PromptManager
from schema import CatalogResponse
from token_counter import estimate_cost

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "w1-env"))            # 确认已插入

from src.llm.router import RouterClient

promptPath = Path(__file__).parent.parent / "prompts" / "catalog_radar" / "music-library-few-shot.md"
version = "v1_fewshot"
m = PromptManager(Path(__file__).parent.parent / "prompts" / "catalog_radar")
# systemPrompt = promptPath.read_text()
systemPrompt= v1 = m.load(version = version, agent_name="小曲", agent_title="曲库雷达", max_candidates=10)

# print(systemPrompt)

test_query = "给连锁健身房找 10 首背景音乐，BPM 120 以上，副歌具有爆发力，预算每年 5 万"

message = [
    {"role": 'system', "content": systemPrompt},
    {"role": "user", "content": test_query}
]

async def main() -> None:
    tier = 'light'
    client: RouterClient = RouterClient(tier=tier)
    print('tier:', tier)
    raw_output = ""
    print(systemPrompt)
    async for token in client.chat_stream(messages=message):
        print(token, end="", flush=True)
        raw_output += token
    response = CatalogResponse(**json.loads(raw_output))
    print("\n✅ 校验通过:", response.candidates[0].song_name)
    
    # reply, usage = await client.chat_sync(message)
    # print("====== usage:", version)
    # print(usage)
    # print(estimate_cost(usage.prompt_tokens, usage.completion_tokens, tier))  # 看结构

if __name__ == "__main__":
    asyncio.run(main())