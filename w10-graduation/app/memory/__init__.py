"""app/memory/__init__.py — 记忆层（复用 W8）

把 W8 的 ShortTermMemory / LongTermMemory 包装成毕业项目专用。

用法：
    mem = build_memory(data_dir="./data")
    mem.short.add_user("你好")
    mem.long.remember("用户偏好", {"style": "电子摇滚"})
"""

import sys
from pathlib import Path

_WORKMUSIC = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_WORKMUSIC / "w8-agent-arch" / "src"))

from memory import LongTermMemory, ShortTermMemory  # noqa: E402


class GraduationMemory:
    """毕业项目记忆封装：短期（会话）+ 长期（跨会话）。"""

    def __init__(self, data_dir: str = "./data") -> None:
        """初始化。

        Args:
            data_dir: 长期记忆文件目录
        """
        import os
        os.makedirs(data_dir, exist_ok=True)
        self.short = ShortTermMemory()
        self.long = LongTermMemory(path=str(Path(data_dir) / "memory.json"))

    def reset_session(self) -> None:
        """新会话开始时清空短期记忆（长期保留）。"""
        self.short.clear()


def build_memory(data_dir: str = "./data") -> GraduationMemory:
    """工厂函数。"""
    return GraduationMemory(data_dir=data_dir)
