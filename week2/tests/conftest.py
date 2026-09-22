from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ..app import db
from ..app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Use an isolated SQLite file per test so API tests do not touch the dev database."""
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "app.db")
    db.init_db()
    with TestClient(app) as c:
        yield c
