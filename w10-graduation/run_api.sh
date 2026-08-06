#!/bin/bash
# 启动毕业项目 FastAPI 服务
# 用法：./run_api.sh

set -e
cd "$(dirname "$0")"

# 用 w1-env 的 venv
source ../w1-env/.venv/bin/activate

# 启动服务（--reload 开发模式）
export PYTHONPATH=.
echo "启动 FastAPI: http://localhost:8000 (docs: /docs)"
uvicorn app.api:app --host 0.0.0.0 --port 8000
