import json

import tiktoken

enc = tiktoken.get_encoding("cl100k_base")

""" token 预算 """
class TokenBudget():
    def __init__(self, model_window:int = 128_000, budget_ratio: float = 0.8):
        self.model_window:int = model_window
        self.budget_ratio:float = budget_ratio
        self.budget: int = int(self.model_window * self.budget_ratio)

    def count(self, messages: list[dict[str, str]]) -> int:
        """计算消息的 token 数量,  先按 4 个字符计算计算"""
        # return sum(int(len(message.get("content", "")) / 4) for message in messages)
        return len(enc.encode(json.dumps(messages, ensure_ascii=False)))
        # return sum(len(enc.encode(message.get("content", ""))) for message in messages)

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
