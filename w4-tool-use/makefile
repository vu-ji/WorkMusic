SHELL := /bin/bash
.PHONY: test run-e2e

test:
	cd ../w1-env && source .venv/bin/activate && cd ../w4-tool-use && python -m pytest src/test_tool.py -v

run-e2e:
	cd ../w1-env && source .venv/bin/activate && cd ../w4-tool-use && python src/test_agent.py
