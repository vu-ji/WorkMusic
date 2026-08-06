# WorkMusic · 版权交易 Agent 工作台

> **一个音乐版权交易的 Agent 工作台**：曲库雷达（语义选曲）+ 合同哨兵（合同审查），通过共享工作区上下文串联完整交易链路 —— 找歌 → 报价（mock）→ 审合同。
> 对标方向：AI Agent 应用开发工程师 ｜ 当前阶段：W10 毕业冲刺

## 本项目是一个 Harness Engineering 项目

项目本身不是一个"写好的应用"，而是一个 **由规格驱动、Agent 可执行的工程 harness**：

- **[AGENTS.md](AGENTS.md)** — 项目说明书，任何 LLM 进入仓库的第一入口
- **[docs/milestones.md](docs/milestones.md)** — W10–W12 任务清单（唯一事实来源，勾选即进度）
- **[docs/prd.md](docs/prd.md)** — 产品需求文档（v0.5 已拍板）
- **[docs/conventions.md](docs/conventions.md)** — 开发规范
- **[.pi/](.pi/)** — Pi Coding Agent 的项目级 harness（工作法 + 任务模板 + 技能）

**驱动方式**：在仓库根目录运行 `pi`，然后：

```
/plan T-101        # 规划任务
/implement T-101   # 实现任务（从零实现 → 写代码 → 跑测试 → 勾选）
/review            # 代码审查
/commit            # 规范提交
/retro M1          # 里程碑复盘
```

## 快速开始

```bash
# 后端
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # 填入 LLM API key
python -m pytest          # 跑测试
uvicorn app.main:app --reload   # 启动服务（http://localhost:8000/health）

# 前端（M4 起）
cd frontend && npm install && npm run dev
```

## 架构一览

```
React 工作台（SSE 流式 UI · Citation 双栏联动 · 观测面板）
        │
Agent 服务层（FastAPI + 手写 Runtime）—— 曲库雷达 · 合同哨兵 · orchestrator
        │
pgvector（向量 + 业务库）    Redis（缓存 + 打标队列）
```

详见 [docs/architecture.md](docs/architecture.md)。

## 数据与版权声明

- 数据底座：[dengxiuqi/ChineseLyrics](https://github.com/dengxiuqi/ChineseLyrics)（102,197 首真实中文歌词，**仅供学习交流使用**，歌词版权属原版权方）
- 本项目本地开发使用该歌词库；**对外部署版仅展示歌词片段（≤2 句）**，不出接口返回完整歌词
- 真实生产场景应接入正版曲库 API，歌词仅用于检索验证

## 学习项目背景

本仓库是作者 12 周「前端 → Agent 开发」转型的毕业项目（W10–W12），从零实现。
