SHELL := /bin/bash
.PHONY: list render run clean

# 列出所有可用版本
test-manager:
	cd ../w1-env && source .venv/bin/activate && cd ../w2-prompts  && python src/test_manager.py

# 跑完整测试（渲染 + 调用模型）
run: 
	cd ../w1-env && source .venv/bin/activate && cd ../w2-prompts && ROUTER_DEFAULT_TIER=middle python src/test_prompt.py

run-ab: 
	cd ../w1-env && source .venv/bin/activate && cd ../w2-prompts && ROUTER_DEFAULT_TIER=light python src/test_ab.py

run-model: 
	cd ../w1-env && source .venv/bin/activate && cd ../w2-prompts && ROUTER_DEFAULT_TIER=light python src/test_model.py

run-light: 
	cd ../w1-env && source .venv/bin/activate && cd ../w2-prompts && ROUTER_DEFAULT_TIER=light python src/test_prompt.py

run-heavy: 
	cd ../w1-env && source .venv/bin/activate && cd ../w2-prompts && ROUTER_DEFAULT_TIER=heavy python src/test_prompt.py

run-deepseek: 
	cd ../w1-env && source .venv/bin/activate && cd ../w2-prompts && ROUTER_DEFAULT_TIER=deepseek python src/test_prompt.py

# 清空 pycache
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
