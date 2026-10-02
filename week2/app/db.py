from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator, Optional

from .config import get_settings


def ensure_data_directory_exists() -> None:
    get_settings().data_dir.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    ensure_data_directory_exists()
    # 连接到数据库
    connection = sqlite3.connect(get_settings().db_path)
    # 将数据库结果转换为字典
    connection.row_factory = sqlite3.Row
    # SQLite 默认关闭外键检查，必须对每个连接打开，CREATE TABLE 里的 FOREIGN KEY 才会生效。
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def _cursor() -> Iterator[sqlite3.Cursor]:
    """Open a connection, yield one cursor, commit on success."""
    with get_connection() as connection:
        cursor = connection.cursor()
        yield cursor
        connection.commit()


def init_db() -> None:
    with _cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS action_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id INTEGER,
                text TEXT NOT NULL,
                done INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (note_id) REFERENCES notes(id)
            );
            """
        )


def insert_note(content: str) -> int:
    with _cursor() as cursor:
        cursor.execute("INSERT INTO notes (content) VALUES (?)", (content,))
        return int(cursor.lastrowid)


def list_notes() -> list[sqlite3.Row]:
    with _cursor() as cursor:
        cursor.execute("SELECT id, content, created_at FROM notes ORDER BY id DESC")
        return list(cursor.fetchall())


def get_note(note_id: int) -> Optional[sqlite3.Row]:
    with _cursor() as cursor:
        cursor.execute(
            "SELECT id, content, created_at FROM notes WHERE id = ?",
            (note_id,),
        )
        return cursor.fetchone()


def insert_action_items(items: list[str], note_id: Optional[int] = None) -> list[int]:
    with _cursor() as cursor:
        ids: list[int] = []
        for item in items:
            cursor.execute(
                "INSERT INTO action_items (note_id, text) VALUES (?, ?)",
                (note_id, item),
            )
            ids.append(int(cursor.lastrowid))
        return ids


def list_action_items(note_id: Optional[int] = None) -> list[sqlite3.Row]:
    with _cursor() as cursor:
        if note_id is None:
            cursor.execute(
                "SELECT id, note_id, text, done, created_at FROM action_items ORDER BY id DESC"
            )
        else:
            cursor.execute(
                "SELECT id, note_id, text, done, created_at FROM action_items WHERE note_id = ? ORDER BY id DESC",
                (note_id,),
            )
        return list(cursor.fetchall())


def mark_action_item_done(action_item_id: int, done: bool) -> bool:
    """Return True if a row was updated; False if id does not exist."""
    with _cursor() as cursor:
        cursor.execute(
            "UPDATE action_items SET done = ? WHERE id = ?",
            (1 if done else 0, action_item_id),
        )
        return cursor.rowcount > 0
