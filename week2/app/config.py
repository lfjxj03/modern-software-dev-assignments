"""Application settings loaded from the environment (and optional .env)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

_WEEK2_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    db_path: Path
    ollama_model: str
    frontend_dir: Path
    app_title: str

# 通过装饰器缓存设置，避免重复加载，运行期间这个函数实际只会执行一次
@lru_cache
def get_settings() -> Settings:
    load_dotenv()
    data_dir = Path(os.getenv("WEEK2_DATA_DIR", str(_WEEK2_ROOT / "data")))
    db_path_raw = os.getenv("WEEK2_DB_PATH")
    db_path = Path(db_path_raw) if db_path_raw else data_dir / "app.db"
    return Settings(
        data_dir=data_dir,
        db_path=db_path,
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
        frontend_dir=_WEEK2_ROOT / "frontend",
        app_title=os.getenv("WEEK2_APP_TITLE", "Action Item Extractor"),
    )
