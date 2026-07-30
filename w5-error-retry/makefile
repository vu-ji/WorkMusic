SHELL := /bin/bash
.PHONY: test

test:
	cd ../w1-env && source .venv/bin/activate && cd ../w5-error-retry && python -m pytest src/test_retry.py -v
