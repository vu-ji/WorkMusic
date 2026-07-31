"""W5 pytest 测试 —— 重试控制器 + 熔断器"""

import asyncio

import pytest
from retry_controller import RetryController, ErrorCategory, CircuitState


class TestErrorCategorization:
    """测试错误分类"""

    def test_timeout_is_transient(self):
        ctrl = RetryController()
        assert ctrl.categorize_error(asyncio.TimeoutError()) == ErrorCategory.TRANSIENT

    def test_connection_error_is_transient(self):
        ctrl = RetryController()
        assert ctrl.categorize_error(ConnectionError("refused")) == ErrorCategory.TRANSIENT

    def test_os_error_is_transient(self):
        ctrl = RetryController()
        assert ctrl.categorize_error(OSError("network down")) == ErrorCategory.TRANSIENT

    def test_type_error_is_permanent(self):
        ctrl = RetryController()
        assert ctrl.categorize_error(TypeError("bad type")) == ErrorCategory.PERMANENT

    def test_value_error_is_permanent(self):
        ctrl = RetryController()
        assert ctrl.categorize_error(ValueError("invalid")) == ErrorCategory.PERMANENT


class TestRetryController:
    """测试重试行为"""

    @pytest.mark.asyncio
    async def test_first_attempt_succeeds(self):
        """第一次就成功——不重试，直接返回"""
        ctrl = RetryController(max_retries=3)

        async def ok_fn():
            return {"data": "ok"}

        result = await ctrl.try_with_retry(ok_fn)
        assert result["success"] is True
        assert result["result"] == {"data": "ok"}

    @pytest.mark.asyncio
    async def test_retry_then_succeed(self):
        """前两次失败（超时），第三次成功"""
        ctrl = RetryController(max_retries=3, backoff_base=0.01)

        call_count = 0

        async def flaky_fn():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise asyncio.TimeoutError("timeout")
            return {"data": "ok"}

        result = await ctrl.try_with_retry(flaky_fn)
        assert result["success"] is True
        assert result["result"] == {"data": "ok"}
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_all_retries_exhausted(self):
        """所有重试耗尽——返回 exhausted=True"""
        ctrl = RetryController(max_retries=2, backoff_base=0.01)

        async def always_fail():
            raise ConnectionError("refused")

        result = await ctrl.try_with_retry(always_fail)
        assert result["success"] is False
        assert result["retries_exhausted"] is True
        assert result["attempts"] == 3  # 1 次初始 + 2 次重试

    @pytest.mark.asyncio
    async def test_permanent_error_no_retry(self):
        """永久错误立即返回，不重试"""
        ctrl = RetryController(max_retries=3, backoff_base=0.01)

        call_count = 0

        async def type_error_fn():
            nonlocal call_count
            call_count += 1
            raise TypeError("bad arg")

        result = await ctrl.try_with_retry(type_error_fn)
        assert result["success"] is False
        assert result["retries_exhausted"] is False
        assert call_count == 1  # 不重试，只调了一次


class TestCircuitBreaker:
    """测试熔断器"""

    def test_circuit_closed_by_default(self):
        ctrl = RetryController()
        assert ctrl.circuit_state == CircuitState.CLOSED
        assert ctrl.is_circuit_open() is False

    def test_circuit_opens_after_threshold(self):
        ctrl = RetryController(
            circuit_breaker_threshold=3,
            circuit_cooldown=9999,
        )
        # 连续 3 次失败
        for _ in range(3):
            ctrl._on_failure()
        assert ctrl.circuit_state == CircuitState.OPEN
        assert ctrl.is_circuit_open() is True

    def test_circuit_stays_closed_below_threshold(self):
        ctrl = RetryController(
            circuit_breaker_threshold=5,
            circuit_cooldown=9999,
        )
        for _ in range(4):
            ctrl._on_failure()
        assert ctrl.circuit_state == CircuitState.CLOSED

    def test_half_open_after_cooldown(self):
        ctrl = RetryController(
            circuit_breaker_threshold=1,
            circuit_cooldown=-10,  # 负数让冷却立刻过期
        )
        ctrl._on_failure()  # 触发熔断
        assert ctrl.is_circuit_open() is False  # 冷却过期 → 进入半开
        assert ctrl.circuit_state == CircuitState.HALF_OPEN

    def test_half_open_to_closed_on_success(self):
        ctrl = RetryController(
            circuit_breaker_threshold=1,
            circuit_cooldown=-10,
        )
        ctrl._on_failure()  # 熔断
        ctrl.is_circuit_open()  # 冷却 → 半开
        ctrl._on_success()  # 成功 → 关闭
        assert ctrl.circuit_state == CircuitState.CLOSED
