"""app/api.py — 毕业项目 FastAPI 接口

启动：uvicorn app.api:app --reload --port 8000

接口：
- GET  /health           健康检查
- POST /chat             对话（多轮会话，session_id 隔离短期记忆）
- GET  /memory           查看长期记忆
- DELETE /memory/{key}   删除一条长期记忆
"""

import sys
import uuid
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.agent import GraduationAgent
from app.memory import build_memory
from app.tools import build_tools

app = FastAPI(title="毕业项目：个人知识库问答 Agent", version="1.0.0")

# 全局组件（跨请求复用；短期记忆按 session_id 隔离）
_memory = build_memory(data_dir="./data")
_tools = build_tools()
_sessions: dict[str, GraduationAgent] = {}


class ChatRequest(BaseModel):
    query: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    steps: int
    session_id: str


class MemoryItem(BaseModel):
    key: str
    value: Any


def _get_agent(session_id: str) -> GraduationAgent:
    """获取或创建会话对应的 Agent（每个会话独立短期记忆）。"""
    if session_id not in _sessions:
        agent = GraduationAgent(
            tools=_tools,
            short_memory=_memory.short,
            long_memory=_memory.long,
        )
        _sessions[session_id] = agent
    return _sessions[session_id]


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query 不能为空")

    session_id = req.session_id or str(uuid.uuid4())
    agent = _get_agent(session_id)
    result = await agent.run(req.query)

    return ChatResponse(
        reply=result.get("reply", ""),
        steps=result.get("steps", 0),
        session_id=session_id,
    )


@app.get("/memory")
async def list_memory() -> dict[str, list[dict]]:
    return {"facts": _memory.long.recall()}


@app.delete("/memory/{key}")
async def forget_memory(key: str) -> dict[str, str]:
    _memory.long.forget(key)
    return {"status": "deleted", "key": key}
