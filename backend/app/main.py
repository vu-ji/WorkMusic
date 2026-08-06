"""WorkMusic Agent 服务层入口。

Milestone 规划（见 docs/milestones.md）：
- M2 接入 RAG 检索
- M3 接入 Agent Runtime（复用 W8 react.py）+ 工具层（复用 W4）
- M4 起提供 SSE 流式接口供前端调用

本文件为最小可跑骨架，后续由 Agent 按 harness 规格填充。
"""

from fastapi import FastAPI

app = FastAPI(
    title="WorkMusic Agent Service",
    description="音乐版权交易 Agent 工作台 · 后端服务（曲库雷达 / 合同哨兵 / orchestrator）",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict:
    """健康检查：验证服务可跑。"""
    return {"status": "ok", "service": "workmusic-backend"}


@app.get("/")
def root() -> dict:
    """入口摘要，方便 Agent 自检。"""
    return {
        "service": "workmusic-backend",
        "docs": "/docs",
        "health": "/health",
        "milestones": "见仓库 docs/milestones.md",
    }
