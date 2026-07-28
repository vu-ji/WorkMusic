SHELL := /bin/bash
.PHONY: list render run clean

# 跑完整测试（渲染 + 调用模型）
run: 
	cd ../w1-env && source .venv/bin/activate && cd ../w3-context && python src/test_budget.py

run-e2e: 
	cd ../w1-env && source .venv/bin/activate && ROUTER_DEFAULT_TIER=middle cd ../w3-context && python src/test_e2e.py
