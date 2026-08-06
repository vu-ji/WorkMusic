import json

# tiktoken 词表需要联网下载（openai blob）。local-first 环境可能失败，
# 降级为字符估算（与 RouterClient 的 Ollama usage=0 fallback 同思路）。
try:
    import tiktoken

    _enc = tiktoken.get_encoding("cl100k_base")
except Exception:
    _enc = None

""" token 预算 """
class TokenBudget():
    def __init__(self, model_window:int = 128_000, budget_ratio: float = 0.8):
        self.model_window:int = model_window
        self.budget_ratio:float = budget_ratio
        self.budget: int = int(self.model_window * self.budget_ratio)

    def count(self, messages: list[dict[str, str]]) -> int:
        """计算消息的 token 数量。

        tiktoken 可用时精确计数；词表下载失败时降级为 4 字符 ≈ 1 token 估算。
        """
        if _enc is not None:
            return len(_enc.encode(json.dumps(messages, ensure_ascii=False)))
        return sum(int(len(m.get("content", "")) / 4) for m in messages)

    def is_within_budget(self, messages: list[dict[str, str]], max_output: int = 0) -> tuple[bool, int, int]:
        """判断消息是否在预算内、当前用量、剩余额度"""
        total_tokens:int = self.count(messages)
        if total_tokens > self.budget:
            return False, total_tokens, self.budget - total_tokens
        if max_output > 0 and total_tokens + max_output > self.budget:
            return False, total_tokens, self.budget - total_tokens
        return True, total_tokens, self.budget - total_tokens

    def trim(self, messages: list[dict[str, str]], max_tokens: int) -> list[dict[str, str]]:
        """ message 根据 token 数量截断"""
        userResult: list[dict[str, str]] = []
        systemMessage:list[dict[str, str]] = []
        userMessage: list[dict[str, str]] = []
        for message in messages:
            if message["role"] == "system":
                systemMessage.append(message)
            else:
                userMessage.append(message)
        systemMsgCount:int = self.count(systemMessage)

        if systemMsgCount >= max_tokens:
            return systemMessage

        userMessage.reverse()
        userMsgCount:int = 0
        for message in userMessage:
            userMsgCount += self.count([message]) 
            if userMsgCount > max_tokens - systemMsgCount:
                break
            userResult.append(message)
        userResult.reverse()
        return systemMessage + userResult
