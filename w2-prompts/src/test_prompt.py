
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))  # 把自己的 src/ 加进去
from prompt_render import load_prompt

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "w1-env"))            # 确认已插入

from src.llm.router import RouterClient

promptPath = Path(__file__).parent.parent / "prompts" / "catalog_radar" / "music-library.md"

# systemPrompt = promptPath.read_text()
systemPrompt= load_prompt(
    Path("prompts/catalog_radar/prompt.yaml"),
    agent_name="小曲",
    agent_title="曲库雷达",
    max_candidates=10,
)

test_query = "给连锁健身房找 10 首背景音乐，BPM 120 以上，副歌具有爆发力，预算每年 5 万"

message = [
    {"role": 'system', "content": systemPrompt},
    {"role": "user", "content": test_query}
]

async def main() -> None:
    client: RouterClient = RouterClient()

    async for token in client.chat_stream(messages=message):
        print(token, end = "", flush=True)
    print()

if __name__ == "__main__":
    asyncio.run(main())