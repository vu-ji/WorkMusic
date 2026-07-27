"""测试 PromptManager 版本加载"""
from pathlib import Path
from prompt_manager import PromptManager

m = PromptManager(Path("prompts/catalog_radar"))
print("版本:", m.list_versions())
print()

v0 = m.load("v0", agent_name="小曲", agent_title="曲库雷达", max_candidates=10)
print("=== v0 前 200 字 ===")
print(v0[:200])
print()

v1 = m.load("v1_fewshot", agent_name="小曲", agent_title="曲库雷达", max_candidates=10)
print("=== v1_fewshot 前 200 字 ===")
print(v1[:200])


pm = PromptManager(Path("prompts/contract_guard"))
print(pm.list_versions())
print(pm.load("v0", agent_name="阿守", agent_title="合同哨兵", max_risks=5)[:200])

