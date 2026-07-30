"""W5 pytest 测试 —— 重试控制器 + 熔断器"""

import pytest

# TODO: from retry_controller import RetryController, ErrorCategory


class TestErrorCategorization:
    """测试错误分类"""

    def test_timeout_is_transient(self):
        """超时错误是可重试的瞬时错误"""
        pass

    def test_connection_error_is_transient(self):
        """连接错误是可重试的"""
        pass

    def test_type_error_is_permanent(self):
        """类型错误不可重试——重试也不会变对"""
        pass

    def test_value_error_is_permanent(self):
        """值错误不可重试"""
        pass


class TestRetryController:
    """测试重试行为"""

    @pytest.mark.asyncio
    async def test_first_attempt_succeeds(self):
        """第一次就成功——不重试，直接返回"""
        pass

    @pytest.mark.asyncio
    async def test_retry_then_succeed(self):
        """前两次失败（瞬时错误），第三次成功"""
        pass

    @pytest.mark.asyncio
    async def test_all_retries_exhausted(self):
        """所有重试都失败——返回 exhausted=True"""
        pass

    @pytest.mark.asyncio
    async def test_permanent_error_no_retry(self):
        """永久错误立即返回，不重试"""
        pass


class TestCircuitBreaker:
    """测试熔断器"""

    def test_circuit_closed_by_default(self):
        """初始状态熔断器关闭（允许调用）"""
        pass

    def test_circuit_opens_after_threshold(self):
        """连续失败达到阈值 → 熔断器打开"""
        pass

    def test_half_open_after_timeout(self):
        """熔断后等待一段时间 → 进入半开状态 → 下次成功则关闭"""
        pass
