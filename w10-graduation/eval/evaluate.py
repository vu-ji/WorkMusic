"""eval/evaluate.py — W12 评估脚本

20+ query 批量评估毕业项目：
- 成功率（有回复 + 不报错）
- 平均轮次
- 工具命中分布（search_catalog / knowledge_search / 无工具）
- 分类统计（曲库类 / 知识类 / 综合类）

用法：
    cd w10-graduation && PYTHONPATH=. python eval/evaluate.py
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agent import GraduationAgent
from app.memory import build_memory
from app.tools import build_tools

# 评估 query 集：覆盖三类
QUERIES = [
    # 曲库类（search_catalog）
    "找一首电子摇滚 BPM 130-150 的歌",
    "有没有适合健身房的动感歌曲",
    "推荐一首 BPM 100 左右的古典钢琴曲",
    "预算 2000 以内找电子摇滚",
    "来一首 BPM 140 的歌",
    "找流行风格的歌",
    "有没有重金属摇滚可以宣泄情绪",
    "找一首 BPM 90 的慢歌",
    "预算 5000 的 hip-hop 歌曲",
    "给我一首电子的歌",
    # 知识类（knowledge_search）
    "电子摇滚适合什么运动场景？",
    "古典钢琴曲适合什么场景？",
    "BPM 130-150 适合什么训练？",
    "RAG 是什么？",
    "混合检索和向量检索有什么区别？",
    "重金属适合什么场景？",
    "hip-hop 适合什么运动？",
    "为什么需要重排序？",
    # 综合类（可能多工具）
    "适合健身房的电子摇滚一般多少钱？",
    "帮我分析古典音乐的使用场景和大概价格",
    "慢节奏音乐适合什么场景？",
    "BPM 140 的歌适合什么运动？",
]


async def run_one(agent, query: str) -> dict:
    """跑单个 query，记录结果。"""
    try:
        result = await agent.run(query)
        trace = result.get("trace", [])
        tool_used = [t["action"] for t in trace if t.get("action") != "Final Answer"]
        return {
            "query": query,
            "ok": bool(result.get("reply")),
            "steps": result.get("steps", 0),
            "tools": tool_used,
            "reply_len": len(result.get("reply", "")),
        }
    except Exception as e:
        return {"query": query, "ok": False, "steps": 0, "tools": [], "error": str(e)}


async def main() -> None:
    print("=" * 60)
    print(f"W12 评估：{len(QUERIES)} 个 query")
    print("=" * 60)

    memory = build_memory(data_dir="./data/eval_memory")
    tools = build_tools()
    agent = GraduationAgent(tools=tools, short_memory=memory.short, long_memory=memory.long)

    results = []
    for i, q in enumerate(QUERIES, 1):
        print(f"[{i}/{len(QUERIES)}] {q[:30]}...")
        r = await run_one(agent, q)
        results.append(r)

    # 统计
    ok = sum(1 for r in results if r["ok"])
    total_steps = sum(r["steps"] for r in results)
    avg_steps = total_steps / len(results) if results else 0

    tool_counts = {"search_catalog": 0, "knowledge_search": 0}
    no_tool = 0
    for r in results:
        if not r["tools"]:
            no_tool += 1
        for t in r["tools"]:
            if t in tool_counts:
                tool_counts[t] += 1

    print("\n" + "=" * 60)
    print("评估结果")
    print("=" * 60)
    print(f"成功率: {ok}/{len(results)} ({ok/len(results)*100:.0f}%)")
    print(f"平均轮次: {avg_steps:.1f}")
    print(f"工具命中: search_catalog={tool_counts['search_catalog']}, "
          f"knowledge_search={tool_counts['knowledge_search']}")
    print(f"无工具 query: {no_tool}")

    # 失败的列出
    failed = [r for r in results if not r["ok"]]
    if failed:
        print("\n失败项:")
        for f in failed:
            print(f"  ❌ {f['query'][:40]} | {f.get('error', '空回复')[:50]}")

    # 存 JSON
    out = Path(__file__).parent / "eval_results.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"summary": {
            "total": len(results), "ok": ok,
            "success_rate": round(ok / len(results), 2),
            "avg_steps": round(avg_steps, 1),
            "tool_counts": tool_counts, "no_tool": no_tool,
        }, "results": results}, f, ensure_ascii=False, indent=2)
    print(f"\n结果已存: {out}")


if __name__ == "__main__":
    asyncio.run(main())
