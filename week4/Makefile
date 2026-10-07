# 启动 FastAPI 开发服务器，支持热重载
.PHONY: run test format lint seed

# 启动开发服务器（热重载模式，默认端口8000）
run:
	PYTHONPATH=. uvicorn backend.app.main:app --reload --host $${HOST:-127.0.0.1} --port $${PORT:-8000}

# 运行后端测试
test:
	PYTHONPATH=. pytest -q backend/tests

# 格式化代码（使用 black 和 ruff）
format:
	black .
	ruff check . --fix

# 检查代码风格
lint:
	ruff check .

# 初始化数据库（应用种子数据）
seed:
	PYTHONPATH=. python -c "from backend.app.db import apply_seed_if_needed; apply_seed_if_needed()"