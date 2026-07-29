"""TokenBudget pytest 测试 —— 6 个用例，期望值基于 tiktoken cl100k_base"""
from token_budget import TokenBudget


def test_count():
    tb = TokenBudget()
    msgs = [
        {"role": "system", "content": "A" * 40},
        {"role": "user", "content": "B" * 80},
        {"role": "assistant", "content": "C" * 120},
    ]
    # tiktoken json.dumps: 90 tokens（含 JSON 结构开销）
    assert tb.count(msgs) == 90


def test_within_budget_ok():
    tb = TokenBudget(model_window=1000, budget_ratio=0.8)  # budget=800
    msgs = [{"role": "user", "content": "x" * 800}]  # 113 tokens
    assert tb.is_within_budget(msgs) == (True, 113, 687)


def test_within_budget_over():
    tb = TokenBudget(model_window=1000, budget_ratio=0.8)
    # 需要超过 budget=800，"x" * 8000 → 远超 800
    msgs = [{"role": "user", "content": "x" * 8000}]
    ok, current, remaining = tb.is_within_budget(msgs)
    assert ok is False
    assert current > 800
    assert remaining < 0


def test_within_budget_max_output():
    tb = TokenBudget(model_window=1000, budget_ratio=0.8)
    # total=788（<800），但 +300 max_output → 超预算
    msgs = [{"role": "user", "content": "y" * 6000}]
    ok, current, remaining = tb.is_within_budget(msgs, max_output=300)
    assert ok is False
    # 第一个 return 值：current 是 total_tokens（输入本身），不是 total+max_output
    assert remaining < 0


def test_trim_keep_system():
    tb = TokenBudget()
    sys = {"role": "system", "content": "S" * 400}   # 213 tokens
    u1  = {"role": "user", "content": "1" * 800}      # ~278
    u2  = {"role": "user", "content": "2" * 800}
    u3  = {"role": "user", "content": "3" * 800}
    # 全部 1047 token，max_tokens=500，只够 system + 1 条最新用户消息
    result = tb.trim([sys, u1, u2, u3], max_tokens=500)
    assert result[0]["role"] == "system"
    assert result[0]["content"].startswith("S")
    # 从最新开始保留：只够装 u3（278 < 500-213=287）
    assert len(result) == 2
    assert result[1]["content"].startswith("3")


def test_trim_system_exceeds():
    tb = TokenBudget()
    sys = {"role": "system", "content": "S" * 400}  # 213 tokens
    u1  = {"role": "user", "content": "1" * 400}
    # max_tokens=50 < system(213) → 静默只返回 system
    result = tb.trim([sys, u1], max_tokens=50)
    assert result == [sys]
