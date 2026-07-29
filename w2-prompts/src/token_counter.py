FEE_Config = {
     "light": {
        "input": 2,
        "output": 8,
    },
    "middle": {
        "input": 2.5,
        "output": 10,
    },
    "heavy": {
        "input": 4,
        "output": 16,
    }       
}
def estimate_cost(prompt_tokens, completion_tokens, tier: str):
    """根据模型定价估算本次请求成本"""
    input_cost = prompt_tokens * FEE_Config[tier]["input"] / 1_000_000
    output_cost = completion_tokens * FEE_Config[tier]["output"] / 1_000_000
    return input_cost + output_cost
