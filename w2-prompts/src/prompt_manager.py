"""Prompt 版本管理器 —— 加载、切换、列出版本的入口"""
import glob
import os
from pathlib import Path

from prompt_render import PromptRenderer # pyright: ignore[reportImplicitRelativeImport]

class PromptManager:
    """管理一个 Agent 的所有 prompt 版本"""

    def __init__(self, agent_dir: Path) -> None:
        self.agent_dir = agent_dir

    def list_versions(self) -> list[str]:
        """列出所有版本文件名，如 ['v0.yaml', 'v1_fewshot.yaml']"""
        # 👇 你来写：glob 所有 *.yaml 文件，返回文件名列表
        return glob.glob("*.yaml", root_dir=self.agent_dir)

    def load(self, version: str, **variables: dict[str, Any]) -> str:
        """加载指定版本并渲染"""
        # 👇 你来写：拼接路径 → PromptRenderer → render
        if not version.endswith(".yaml"):
            version += ".yaml"
        if version in self.list_versions():
            return PromptRenderer(self.agent_dir / version).render(variables)
        else:
            raise ValueError(f"版本 {version} 不存在")
