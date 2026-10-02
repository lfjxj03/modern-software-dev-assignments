"""配置pytest的测试环境。"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ..app.config import get_settings
from ..app.main import app


@pytest.fixture
# 使用隔离的SQLite文件进行测试，避免测试数据污染开发数据库。
def client(tmp_path, monkeypatch):
    """
    Use an isolated SQLite file per test so API tests do not touch the dev database.
    这可以保证测试时不会污染开发数据库。
    """
    monkeypatch.setenv("WEEK2_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    # TestClient 的 with 会触发 FastAPI lifespan，此时才 init_db（用上面的临时库路径）。
    with TestClient(app) as c:  # 创建测试客户端，模拟HTTP请求（实际是直接调用app，不启动服务器不占用8000端口）。
        yield c
    get_settings.cache_clear()
