"""app/main.py — 毕业项目入口

CLI 版：python app/main.py
TODO (W11): FastAPI 版接口

功能：
- 多轮对话（短期记忆）
- 工具调用（曲库检索 + 知识检索）
- 长期记忆（用户偏好跨会话）
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agent import GraduationAgent
from memory import build_memory
from tools import build_tools


async def main() -> None:
    print("=" * 50)
    print("毕业项目：个人知识库问答 Agent")
    print("输入问题，Ctrl+C 退出")
    print("=" * 50)

    memory = build_memory()
    tools = build_tools()
    agent = GraduationAgent(tools=tools, short_memory=memory.short, long_memory=memory.long)

    while True:
        try:
            query = input("\n你 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not query:
            continue
        if query in ("exit", "quit", "退出"):
            print("再见！")
            break

        try:
            result = await agent.run(query)
            print(f"Agent > {result.get('reply', '（无回复）')}")
            print(f"  (steps={result.get('steps')})")
        except Exception as e:
            print(f"错误: {e}")


if __name__ == "__main__":
    asyncio.run(main())
