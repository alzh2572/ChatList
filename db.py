"""Доступ к SQLite — единственный модуль работы с базой данных."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = Path("chatlist.db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS prompts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT    NOT NULL,
    prompt     TEXT    NOT NULL,
    tags       TEXT
);

CREATE TABLE IF NOT EXISTS models (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL UNIQUE,
    api_url    TEXT    NOT NULL,
    api_id     TEXT    NOT NULL,
    is_active  INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS results (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_id  INTEGER NOT NULL,
    model_id   INTEGER NOT NULL,
    response   TEXT    NOT NULL,
    created_at TEXT    NOT NULL,
    FOREIGN KEY (prompt_id) REFERENCES prompts(id) ON DELETE CASCADE,
    FOREIGN KEY (model_id)  REFERENCES models(id)  ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_prompts_created_at ON prompts(created_at);
CREATE INDEX IF NOT EXISTS idx_models_is_active  ON models(is_active);
CREATE INDEX IF NOT EXISTS idx_results_prompt_id ON results(prompt_id);
CREATE INDEX IF NOT EXISTS idx_results_model_id  ON results(model_id);
CREATE INDEX IF NOT EXISTS idx_results_created_at ON results(created_at);
"""

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Модели OpenRouter (бесплатные)
OPENROUTER_MODELS = [
    {
        "name": "poolside/laguna-xs-2.1:free",
        "api_url": OPENROUTER_API_URL,
        "api_id": "OPENROUTER_API_KEY",
        "is_active": 1,
    },
    {
        "name": "cohere/north-mini-code:free",
        "api_url": OPENROUTER_API_URL,
        "api_id": "OPENROUTER_API_KEY",
        "is_active": 1,
    },
]

SEED_MODELS = OPENROUTER_MODELS

DEFAULT_SETTINGS = {
    "db_path": "chatlist.db",
    "request_timeout": "60",
    "theme": "light",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().replace(microsecond=0).isoformat()


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def get_db_path() -> Path:
    configured = get_setting("db_path", str(DEFAULT_DB_PATH))
    return Path(configured or DEFAULT_DB_PATH)


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(db_path or DEFAULT_DB_PATH)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path | str | None = None) -> None:
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        _seed_defaults(conn)
        _ensure_openrouter_models(conn)
        conn.commit()
    finally:
        conn.close()


def _seed_defaults(conn: sqlite3.Connection) -> None:
    for key, value in DEFAULT_SETTINGS.items():
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )

    count = conn.execute("SELECT COUNT(*) FROM models").fetchone()[0]
    if count == 0:
        for model in SEED_MODELS:
            conn.execute(
                """
                INSERT INTO models (name, api_url, api_id, is_active)
                VALUES (?, ?, ?, ?)
                """,
                (model["name"], model["api_url"], model["api_id"], model["is_active"]),
            )


def _ensure_openrouter_models(conn: sqlite3.Connection) -> None:
    allowed = {model["name"] for model in OPENROUTER_MODELS}

    for model in OPENROUTER_MODELS:
        conn.execute(
            """
            INSERT OR IGNORE INTO models (name, api_url, api_id, is_active)
            VALUES (?, ?, ?, ?)
            """,
            (model["name"], model["api_url"], model["api_id"], model["is_active"]),
        )
        conn.execute(
            """
            UPDATE models
            SET api_url = ?, api_id = ?, is_active = ?
            WHERE name = ?
            """,
            (model["api_url"], model["api_id"], model["is_active"], model["name"]),
        )

    extra = conn.execute(
        "SELECT id, name FROM models WHERE name NOT IN ({})".format(
            ",".join("?" * len(allowed))
        ),
        list(allowed),
    ).fetchall()

    for row in extra:
        conn.execute("DELETE FROM results WHERE model_id = ?", (row["id"],))
        conn.execute("DELETE FROM models WHERE id = ?", (row["id"],))


# --- prompts ---


def create_prompt(prompt: str, tags: str | None = None, db_path: Path | str | None = None) -> int:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "INSERT INTO prompts (created_at, prompt, tags) VALUES (?, ?, ?)",
            (_now_iso(), prompt, tags),
        )
        conn.commit()
        return int(cursor.lastrowid)
    finally:
        conn.close()


def get_prompt(prompt_id: int, db_path: Path | str | None = None) -> dict[str, Any] | None:
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,)).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def list_prompts(db_path: Path | str | None = None) -> list[dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM prompts ORDER BY created_at DESC"
        ).fetchall()
        return [_row_to_dict(row) for row in rows]
    finally:
        conn.close()


def search_prompts(query: str, db_path: Path | str | None = None) -> list[dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        pattern = f"%{query}%"
        rows = conn.execute(
            """
            SELECT * FROM prompts
            WHERE prompt LIKE ? OR IFNULL(tags, '') LIKE ?
            ORDER BY created_at DESC
            """,
            (pattern, pattern),
        ).fetchall()
        return [_row_to_dict(row) for row in rows]
    finally:
        conn.close()


def update_prompt(
    prompt_id: int,
    *,
    prompt: str | None = None,
    tags: str | None = None,
    db_path: Path | str | None = None,
) -> bool:
    fields: list[str] = []
    values: list[Any] = []

    if prompt is not None:
        fields.append("prompt = ?")
        values.append(prompt)
    if tags is not None:
        fields.append("tags = ?")
        values.append(tags)

    if not fields:
        return False

    values.append(prompt_id)
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            f"UPDATE prompts SET {', '.join(fields)} WHERE id = ?",
            values,
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_prompt(prompt_id: int, db_path: Path | str | None = None) -> bool:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# --- models ---


def create_model(
    name: str,
    api_url: str,
    api_id: str,
    is_active: bool = True,
    db_path: Path | str | None = None,
) -> int:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            INSERT INTO models (name, api_url, api_id, is_active)
            VALUES (?, ?, ?, ?)
            """,
            (name, api_url, api_id, int(is_active)),
        )
        conn.commit()
        return int(cursor.lastrowid)
    finally:
        conn.close()


def get_model(model_id: int, db_path: Path | str | None = None) -> dict[str, Any] | None:
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM models WHERE id = ?", (model_id,)).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def list_models(db_path: Path | str | None = None) -> list[dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute("SELECT * FROM models ORDER BY name").fetchall()
        return [_row_to_dict(row) for row in rows]
    finally:
        conn.close()


def list_active_models(db_path: Path | str | None = None) -> list[dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM models WHERE is_active = 1 ORDER BY name"
        ).fetchall()
        return [_row_to_dict(row) for row in rows]
    finally:
        conn.close()


def update_model(
    model_id: int,
    *,
    name: str | None = None,
    api_url: str | None = None,
    api_id: str | None = None,
    is_active: bool | None = None,
    db_path: Path | str | None = None,
) -> bool:
    fields: list[str] = []
    values: list[Any] = []

    if name is not None:
        fields.append("name = ?")
        values.append(name)
    if api_url is not None:
        fields.append("api_url = ?")
        values.append(api_url)
    if api_id is not None:
        fields.append("api_id = ?")
        values.append(api_id)
    if is_active is not None:
        fields.append("is_active = ?")
        values.append(int(is_active))

    if not fields:
        return False

    values.append(model_id)
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            f"UPDATE models SET {', '.join(fields)} WHERE id = ?",
            values,
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_model(model_id: int, db_path: Path | str | None = None) -> bool:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute("DELETE FROM models WHERE id = ?", (model_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# --- results ---


def save_result(
    prompt_id: int,
    model_id: int,
    response: str,
    db_path: Path | str | None = None,
) -> int:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            INSERT INTO results (prompt_id, model_id, response, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (prompt_id, model_id, response, _now_iso()),
        )
        conn.commit()
        return int(cursor.lastrowid)
    finally:
        conn.close()


def save_results_batch(
    prompt_id: int,
    items: list[tuple[int, str]],
    db_path: Path | str | None = None,
) -> int:
    conn = get_connection(db_path)
    try:
        created_at = _now_iso()
        conn.executemany(
            """
            INSERT INTO results (prompt_id, model_id, response, created_at)
            VALUES (?, ?, ?, ?)
            """,
            [(prompt_id, model_id, response, created_at) for model_id, response in items],
        )
        conn.commit()
        return len(items)
    finally:
        conn.close()


def list_results(db_path: Path | str | None = None) -> list[dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT r.*, p.prompt, m.name AS model_name
            FROM results r
            JOIN prompts p ON p.id = r.prompt_id
            JOIN models m ON m.id = r.model_id
            ORDER BY r.created_at DESC
            """
        ).fetchall()
        return [_row_to_dict(row) for row in rows]
    finally:
        conn.close()


def get_results_by_prompt(
    prompt_id: int, db_path: Path | str | None = None
) -> list[dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT r.*, m.name AS model_name
            FROM results r
            JOIN models m ON m.id = r.model_id
            WHERE r.prompt_id = ?
            ORDER BY r.created_at DESC
            """,
            (prompt_id,),
        ).fetchall()
        return [_row_to_dict(row) for row in rows]
    finally:
        conn.close()


def search_results(query: str, db_path: Path | str | None = None) -> list[dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        pattern = f"%{query}%"
        rows = conn.execute(
            """
            SELECT r.*, p.prompt, m.name AS model_name
            FROM results r
            JOIN prompts p ON p.id = r.prompt_id
            JOIN models m ON m.id = r.model_id
            WHERE r.response LIKE ? OR p.prompt LIKE ? OR m.name LIKE ?
            ORDER BY r.created_at DESC
            """,
            (pattern, pattern, pattern),
        ).fetchall()
        return [_row_to_dict(row) for row in rows]
    finally:
        conn.close()


def delete_result(result_id: int, db_path: Path | str | None = None) -> bool:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute("DELETE FROM results WHERE id = ?", (result_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# --- settings ---


def get_setting(key: str, default: str | None = None, db_path: Path | str | None = None) -> str | None:
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return default
        return str(row["value"])
    finally:
        conn.close()


def list_settings(db_path: Path | str | None = None) -> dict[str, str]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute("SELECT key, value FROM settings ORDER BY key").fetchall()
        return {str(row["key"]): str(row["value"]) for row in rows}
    finally:
        conn.close()


def set_setting(key: str, value: str, db_path: Path | str | None = None) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        conn.commit()
    finally:
        conn.close()
