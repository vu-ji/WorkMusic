"""provider/retry.py — Dify 插件 provider 入口

把 W5 RetryController 封装成 Dify 插件工具。

注意：完整的 Dify 插件需要配合 Dify 平台（plugin tooling CLI 打包 + 上传）。
这里实现了 SDK 标准的 Tool 子类，逻辑可独立单测；
平台侧打包（dify plugin package）在部署时执行。
"""

import sys
from pathlib import Path
from typing import Any

# 复用 W5 RetryController 和插件逻辑
_WORKMUSIC = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_WORKMUSIC / "w5-error-retry" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from dify_plugin import Tool  # noqa: E402
from dify_plugin.entities.invoke_message import InvokeMessage  # noqa: E402
from tools.retry_tool import RetryTool as RetryToolCore  # noqa: E402


class RetryTool(Tool):
    """Dify 插件工具：带指数退避重试的操作执行。"""

    def _invoke(
        self,
        tool_parameters: dict[str, Any],
    ) -> Any:
        """执行工具（Dify SDK 要求的 _invoke 签名）。"""
        core = RetryToolCore()
        result = core.invoke(
            operation=tool_parameters.get("operation", "llm_call"),
            max_retries=int(tool_parameters.get("max_retries", 3)),
            simulate_failures=int(tool_parameters.get("simulate_failures", 0)),
        )

        if result.get("success"):
            message = (
                f"✅ 操作成功（尝试 {result.get('attempts')} 次）\n"
                f"结果: {result.get('result')}"
            )
        else:
            message = (
                f"❌ 操作失败（尝试 {result.get('attempts')} 次）\n"
                f"错误: {result.get('error')}"
            )

        # Dify 工具返回消息列表
        return [InvokeMessage(text=message)]


def main() -> None:
    """插件入口（Dify 运行时调用）。"""
    # 标准 Dify 插件以 `python -m provider.retry` 或 plugin 打包方式运行
    from dify_plugin import Plugin

    plugin = Plugin(name="retry-tool")
    plugin.tool(RetryTool)
    plugin.run()


if __name__ == "__main__":
    main()
