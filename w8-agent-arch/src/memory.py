"""memory.py — 多轮对话记忆（短期 + 长期）

W8 核心交付之三。当前 Agent 每次 run() 都从零开始——用户说
"帮我找首歌"、"对，就是那首" 时，"那首"没有上下文。

两种记忆：
1. 短期记忆（对话内）：同一会话的对话历史，放 messages 里
2. 长期记忆（跨会话）：用户偏好、历史事实，存 JSON 文件，启动时加载

前端类比：
- 短期记忆 ≈ React 组件内 state（会话期间有效）
- 长期记忆 ≈ localStorage（跨会话持久）
"""

import json
from pathlib import Path
from typing import Any


class ShortTermMemory:
    """短期记忆：当前会话的消息历史。"""

    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []

    def add_user(self, content: str) -> None:
        """添加用户消息。"""
        self.messages.append({"role": "user", "content": content})

    def add_assistant(self, content: str) -> None:
        """添加助手消息。"""
        self.messages.append({"role": "assistant", "content": content})

    def add_system(self, content: str) -> None:
        """添加系统消息。"""
        self.messages.append({"role": "system", "content": content})

    def get_messages(self) -> list[dict[str, str]]:
        """获取全部消息（供 RouterClient 使用）。"""
        return self.messages

    def clear(self) -> None:
        """清空会话（新会话开始时）。"""
        self.messages = []


class LongTermMemory:
    """长期记忆：跨会话的用户事实，存 JSON 文件。

    用法：
        mem = LongTermMemory(path="./data/memory.json")
        mem.remember("用户偏好", {"style": "电子摇滚"})
        facts = mem.recall()
    """

    def __init__(self, path: str) -> None:
        """初始化。

        Args:
            path: 记忆文件路径（不存在则创建）
        """
        self.path = path
        # 文件已存在 → 加载已有记忆（跨会话持久的关键）
        if Path(path).exists():
            with open(path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        else:
            self.data = {"facts": []}

    def remember(self, key: str, value: Any) -> None:
        """写入一条记忆。"""
        self.data["facts"].append({"key": key, "value": value})
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def recall(self) -> list[dict[str, Any]]:
        """读取全部记忆。"""
        return self.data["facts"]

    def forget(self, key: str) -> None:
        """删除指定 key 的记忆。"""
        self.data["facts"] = [f for f in self.data["facts"] if f["key"] != key]
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
