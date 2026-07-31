"""retry_controller.py — 工具调用重试控制器

W5 核心模块。W4 的 Agent Loop 在工具失败时把错误发给 LLM 修正——这是"语义级重试"。
W5 加的是"工程级重试"：在工具执行层面处理瞬时故障（网络超时、服务暂时不可用），
不依赖 LLM 介入。只有所有工程重试都失败后才报告给 LLM。

两种重试的分工：
- RetryController：处理网络/超时/临时错误 → 透明重试，LLM 无感知
- format_error_for_llm：处理参数校验/业务逻辑错误 → LLM 介入修正

前端类比：
- RetryController ≈ axios-retry（自动重试 5xx，用户无感知）
- format_error ≈ 表单校验 400（用户看到错误，自己修）
"""

import asyncio
import time
from enum import Enum
from typing import Any, Callable, Awaitable


# ============================================================
# 错误分类枚举
# ============================================================

class ErrorCategory(Enum):
    """错误的可重试性判断。

    TRANSIENT（瞬时）——网络超时、连接中断、服务暂时不可用。
        这类错误不是代码 bug，是环境波动。等一会儿大概率能恢复。
        前端类比：fetch 的 503 Service Unavailable → 刷新页面通常能恢复。

    PERMANENT（永久）——参数类型错误、字段缺失、业务规则不匹配。
        这类错误不管重试多少次都一样。需要 LLM 修正参数或人工介入。
        前端类比：TypeError / ReferenceError → 刷新页面不会变对。
    """
    TRANSIENT = "transient"
    PERMANENT = "permanent"


# ============================================================
# 熔断器状态枚举
# ============================================================

class CircuitState(Enum):
    """熔断器三态状态机。

    CLOSED（闭合）→ 正常调用，失败计数器累加。
        连续失败达到 threshold → 进入 OPEN。

    OPEN（断开）→ 直接拒绝所有调用，不再重试。
        等待 cooldown 秒后 → 进入 HALF_OPEN。

    HALF_OPEN（半开）→ 允许一次探测调用。
        探测成功 → 回到 CLOSED（恢复）。
        探测失败 → 回到 OPEN（继续熔断）。

    前端类比：CDN 节点健康检查。
        CLOSED = 正常回源。OPEN = 切到备用节点。HALF_OPEN = 定时探活，恢复后切回。
    """
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


# ============================================================
# 重试控制器
# ============================================================

class RetryController:
    """工具调用重试控制器。

    封装三个机制：
    1. 错误分类 → 瞬时错误才重试，永久错误立即返回
    2. 指数退避 → 每次重试等待时间翻倍（0.5s → 1s → 2s → 4s）
    3. 熔断器 → 连续失败 N 次后直接拒调，防止雪崩

    用法：
        ctrl = RetryController(max_retries=3, backoff_base=0.5)
        result = await ctrl.try_with_retry(
            tool_fn,
            style="电子", bpm_min=120, bpm_max=150, budget=5000,
        )
    """

    def __init__(
        self,
        max_retries: int = 3,
        backoff_base: float = 0.5,
        circuit_breaker_threshold: int = 5,
        circuit_cooldown: float = 30.0,
    ) -> None:
        """
        Args:
            max_retries: 瞬时错误最大重试次数（不含首次尝试）。默认 3 → 1 初始 + 3 重试 = 最多 4 次
            backoff_base: 退避基数（秒）。第 N 次等待 = base * 2^N。默认 0.5s → 0.5/1/2/4s
            circuit_breaker_threshold: 连续失败多少次后触发熔断。默认 5
            circuit_cooldown: 熔断后等待多少秒进入半开状态。默认 30s
        """
        self.max_retries: int = max_retries
        self.backoff_base: float = backoff_base
        self.circuit_threshold: int = circuit_breaker_threshold
        self.circuit_cooldown: float = circuit_cooldown

        # 熔断器内部状态
        self._circuit_state: CircuitState = CircuitState.CLOSED  # 初始：正常调用
        self._consecutive_failures: int = 0              # 连续失败计数
        self._circuit_opened_at: float = 0.0        # 熔断触发时间戳

    # ── 公开接口 ────────────────────────────────────────

    async def try_with_retry(
        self,
        fn: Callable[..., Awaitable[Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """执行工具函数，自动重试瞬时错误。

        流程：
        1. 熔断检查 → 如果熔断器断开，直接拒调
        2. 调用 fn(**kwargs)
        3. 成功 → 重置熔断计数，返回 {"success": True, "result": ...}
        4. 瞬时错误 → 累加失败计数，指数退避后重试
        5. 永久错误 → 立即返回 {"success": False, "error": ...}，不重试
        6. 重试耗尽 → 返回 {"success": False, "retries_exhausted": True}

        Args:
            fn: 要重试的异步工具函数（如 search_catalog）
            **kwargs: 传给 fn 的参数

        Returns:
            {"success": True, "result": ...}  成功
            {"success": False, "error": ..., "retries_exhausted": True/False}  失败
        """
        # 熔断器检查：如果断开则直接拒绝，连重试都不尝试
        if self.is_circuit_open():
            return {
                "success": False,
                "error": "熔断器已打开，拒绝调用",
                "retries_exhausted": False,
            }

        last_error: str = ""

        # range(max_retries + 1) = 1 次初始尝试 + max_retries 次重试
        for attempt in range(self.max_retries + 1):
            try:
                result = await fn(**kwargs)
                # 成功 → 重置连续失败计数，熔断器状态回 CLOSED
                self._on_success()
                return {"success": True, "result": result}
            except Exception as e:
                last_error = str(e)
                category = self.categorize_error(e)

                # 永久错误：不重试，不累加熔断计数
                if category == ErrorCategory.PERMANENT:
                    return {
                        "success": False,
                        "error": last_error,
                        "retries_exhausted": False,
                    }

                # 瞬时错误：累加失败计数（可能触发熔断），等待后退避，下一轮重试
                self._on_failure()
                if attempt < self.max_retries:
                    delay = self.backoff_base * (2 ** attempt)  # 指数退避
                    await asyncio.sleep(delay)

        # 所有重试耗尽 → 返回 exhausted 标记
        return {
            "success": False,
            "error": last_error,
            "retries_exhausted": True,
            "attempts": self.max_retries + 1,
        }

    def categorize_error(self, exception: Exception) -> ErrorCategory:
        """判断异常是可重试还是永久的。

        瞬时（可重试）：网络/IO 层错误，环境问题。
            - asyncio.TimeoutError：异步等待超时
            - ConnectionError：TCP 连接被拒绝或中断
            - OSError：底层系统错误（DNS 解析失败等）
            - TimeoutError：同步超时

        永久（不重试）：代码/逻辑错误，重试无用。
            - TypeError / ValueError / KeyError / AttributeError 等
            → 默认归为 PERMANENT。
        """
        if isinstance(exception, (asyncio.TimeoutError, ConnectionError, OSError, TimeoutError)):
            return ErrorCategory.TRANSIENT
        return ErrorCategory.PERMANENT

    # ── 熔断器 ──────────────────────────────────────────

    def is_circuit_open(self) -> bool:
        """熔断器是否处于断开状态。

        CLOSED → False（允许调用）
        HALF_OPEN → False（允许一次探测）
        OPEN + 未冷却 → True（拒绝）
        OPEN + 已冷却 → 自动转 HALF_OPEN → False（允许探测）
        """
        if self._circuit_state == CircuitState.CLOSED:
            return False
        if self._circuit_state == CircuitState.OPEN:
            # 冷却时间到 → 进入半开，允许一次探测
            if time.monotonic() - self._circuit_opened_at >= self.circuit_cooldown:
                self._circuit_state = CircuitState.HALF_OPEN
                return False
            return True
        # HALF_OPEN 状态：只允许一次探测调用
        return False

    # ── 内部状态方法 ────────────────────────────────────

    def _on_success(self) -> None:
        """调用成功后重置状态。连续失败计数清零。半开状态成功后回到闭合。"""
        self._consecutive_failures = 0
        if self._circuit_state == CircuitState.HALF_OPEN:
            self._circuit_state = CircuitState.CLOSED

    def _on_failure(self) -> None:
        """调用失败后累加计数。达到阈值时触发熔断（CLOSED → OPEN）。"""
        self._consecutive_failures += 1
        if (
            self._consecutive_failures >= self.circuit_threshold
            and self._circuit_state == CircuitState.CLOSED
        ):
            self._circuit_state = CircuitState.OPEN
            self._circuit_opened_at = time.monotonic()

    @property
    def circuit_state(self) -> CircuitState:
        """暴露熔断器当前状态，用于日志/观测面板。"""
        return self._circuit_state
