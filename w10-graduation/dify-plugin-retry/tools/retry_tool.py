"""tools/retry_tool.py — Dify 插件：重试工具

把 W5 的 RetryController 封装成 Dify 插件工具。
Dify 用户在 workflow 里调用此工具时，可以给任意"内部 API 调用"加上重试能力。

注意：这是插件逻辑的独立实现（可脱离 Dify 单测）。
真正的 Dify 插件 SDK 适配（plugin.yaml + provider）在 W11 完成。

用法（独立测试）：
    tool = RetryTool()
    result = tool.invoke(
        operation="llm_call",        # 要重试的操作
        max_retries=3,               # 重试次数
        timeout_seconds=30,          # 超时
    )
"""

import sys
import time
from pathlib import Path
from typing import Any

_WORKMUSIC = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_WORKMUSIC / "w5-error-retry" / "src"))
sys.path.insert(0, str(_WORKMUSIC / "w1-env"))

from retry_controller import RetryController, ErrorCategory  # noqa: E402


class RetryTool:
    """重试工具：模拟一个可能失败的内部调用，验证重试策略。"""

    def __init__(self, base_backoff: float = 0.5) -> None:
        """初始化。

        Args:
            base_backoff: 指数退避基数（秒）
        """
        self.retry = RetryController(max_retries=3, backoff_base=base_backoff)

    def invoke(
        self,
        operation: str = "llm_call",
        max_retries: int = 3,
        simulate_failures: int = 0,
    ) -> dict[str, Any]:
        """执行带重试的操作。

        Args:
            operation: 操作类型（llm_call / http_call / db_query）
            max_retries: 最大重试次数
            simulate_failures: 前 N 次模拟失败（测试用）

        Returns:
            {"success": True, "attempts": N, "result": ...} 或
            {"success": False, "attempts": N, "error": ...}
        """
        # 每次 invoke 用独立的 RetryController（避免状态泄漏）
        ctrl = RetryController(max_retries=max_retries, backoff_base=self.retry.backoff_base)

        # 模拟操作的执行体：前 simulate_failures 次抛 ConnectionError（瞬时）
        # 注意：RetryController 内部 await fn()，必须传 async 函数
        attempt_counter = {"n": 0}

        async def simulated_call():
            attempt_counter["n"] += 1
            return self._simulate_call(operation, attempt_counter["n"] - 1, simulate_failures)

        import asyncio

        result = asyncio.run(ctrl.try_with_retry(simulated_call))
        result["attempts"] = attempt_counter["n"]
        return result

    def _simulate_call(self, operation: str, attempt: int, simulate_failures: int) -> str:
        """模拟内部调用。"""
        if attempt < simulate_failures:
            raise ConnectionError(f"{operation} 第 {attempt+1} 次调用失败（模拟网络错误）")
        return f"{operation} 成功，attempt={attempt + 1}"
