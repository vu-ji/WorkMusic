"""W4 e2e：Agent Loop 全链路验证

需要 ollama 运行中。用法：make run-e2e
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from agent import Agent


async def main():
    agent = Agent("light")

    print("=" * 60)
    print("W4 Agent Loop e2e")
    print("=" * 60)

    # 用例 1：需要调工具的查询
    print("\n--- 用例 1：需要检索曲库 ---")
    r1 = await agent.run("给连锁健身房找 5 首电子摇滚 BGM，BPM 130-150，预算 3000～4000")
    print(f"轮次: {r1['turns']}")
    print(f"工具调用: {len(r1['tool_calls'])} 次")
    for tc in r1["tool_calls"]:
        print(f"  - {tc['tool']}({tc['arguments']}) → success={tc['success']}")
    print(f"回复: {r1['reply'][:300]}")
    if r1.get("error"):
        print(f"错误: {r1['error']}")

    # 用例 2：不需要工具（打招呼）
    print("\n--- 用例 2：不需要工具 ---")
    r2 = await agent.run("你好，你是谁？")
    print(f"轮次: {r2['turns']}")
    print(f"工具调用: {len(r2['tool_calls'])} 次")
    print(f"回复: {r2['reply'][:200]}")
    if r2.get("error"):
        print(f"错误: {r2['error']}")

    # 用例 3：无匹配数据
    print("\n--- 用例 3：预算过低无匹配 ---")
    r3 = await agent.run("找电子摇滚 BPM 120-160，预算只要 100 元")
    print(f"轮次: {r3['turns']}")
    print(f"工具调用: {len(r3['tool_calls'])} 次")
    print(f"回复: {r3['reply'][:300]}")
    if r3.get("error"):
        print(f"错误: {r3['error']}")

    print("\n" + "=" * 60)
    print("W4 e2e 完成")


if __name__ == "__main__":
    asyncio.run(main())
