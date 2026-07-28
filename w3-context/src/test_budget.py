from token_budget import TokenBudget

def test_count():
    tb = TokenBudget()
    msgs = [
        {"role": "system", "content": "A" * 40},
        {"role": "user", "content": "B" * 80},
        {"role": "assistant", "content": "C" * 120},
    ]
    assert tb.count(msgs) == 60, f"expected 60, got {tb.count(msgs)}"

def test_within_budget_ok_and_over():
    tb = TokenBudget(model_window=1000, budget_ratio=0.8)  # budget=800
    ok_msgs = [{"role": "user", "content": "x" * 800}]  # 200 tokens
    assert tb.is_within_budget(ok_msgs) == (True, 200, 600)

    over_msgs = [{"role": "user", "content": "x" * 3400}]  # 850 tokens
    assert tb.is_within_budget(over_msgs) == (False, 850, -50)

def test_within_budget_with_max_output():
    tb = TokenBudget(model_window=1000, budget_ratio=0.8)
    msgs = [{"role": "user", "content": "x" * 2400}]  # 600 tokens
    assert tb.is_within_budget(msgs, max_output=300) == (False, 600, 200)

def test_trim_keep_system():
    tb = TokenBudget()
    sys = {"role": "system", "content": "S" * 400}   # 100 tokens
    u1  = {"role": "user", "content": "1" * 800}      # 200
    u2  = {"role": "user", "content": "2" * 800}
    u3  = {"role": "user", "content": "3" * 800}
    result = tb.trim([sys, u1, u2, u3], max_tokens=500)
    assert result[0]["role"] == "system"
    assert result[0]["content"].startswith("S")
    assert [m["content"][0] for m in result[1:]] == ["2", "3"]
    assert len(result) == 3

def test_trim_system_exceeds():
    tb = TokenBudget()
    sys = {"role": "system", "content": "S" * 400}  # 100 tokens
    u1  = {"role": "user", "content": "1" * 400}
    result = tb.trim([sys, u1], max_tokens=50)
    assert result == [sys]

if __name__ == "__main__":
    test_count()
    print('test_count passed')

    test_within_budget_ok_and_over()
    print('test_within_budget_ok_and_over passed')

    test_within_budget_with_max_output()
    print('test_within_budget_with_max_output passed')

    test_trim_keep_system()
    print('test_trim_keep_system passed')
    
    test_trim_system_exceeds()
    print('test_trim_system_exceeds passed')

    print("all 5 passed")
