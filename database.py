import sqlite3
import time
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent / "bot_data.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS warnings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id     INTEGER NOT NULL,
                user_id     INTEGER NOT NULL,
                warned_by   INTEGER NOT NULL,
                reason      TEXT    NOT NULL,
                created_at  REAL    NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_warnings_chat_user
                ON warnings (chat_id, user_id);

            CREATE TABLE IF NOT EXISTS settings (
                chat_id     INTEGER NOT NULL,
                key         TEXT    NOT NULL,
                value       TEXT    NOT NULL,
                PRIMARY KEY (chat_id, key)
            );

            CREATE TABLE IF NOT EXISTS action_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id     INTEGER NOT NULL,
                admin_id    INTEGER NOT NULL,
                target_id   INTEGER NOT NULL,
                action      TEXT    NOT NULL,
                created_at  REAL    NOT NULL
            );
        """)


def add_warning(chat_id: int, user_id: int, warned_by: int, reason: str) -> int:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO warnings (chat_id, user_id, warned_by, reason, created_at) VALUES (?,?,?,?,?)",
            (chat_id, user_id, warned_by, reason, time.time()),
        )
        count = conn.execute(
            "SELECT COUNT(*) FROM warnings WHERE chat_id=? AND user_id=?",
            (chat_id, user_id),
        ).fetchone()[0]
    return count


def get_warnings(chat_id: int, user_id: int) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT reason, created_at FROM warnings WHERE chat_id=? AND user_id=? ORDER BY created_at",
            (chat_id, user_id),
        ).fetchall()
    return [{"reason": r["reason"], "created_at": r["created_at"]} for r in rows]


def clear_warnings(chat_id: int, user_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM warnings WHERE chat_id=? AND user_id=?",
            (chat_id, user_id),
        )


def set_setting(chat_id: int, key: str, value: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO settings (chat_id, key, value) VALUES (?,?,?) "
            "ON CONFLICT(chat_id, key) DO UPDATE SET value=excluded.value",
            (chat_id, key, value),
        )


def get_setting(chat_id: int, key: str) -> str | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE chat_id=? AND key=?",
            (chat_id, key),
        ).fetchone()
    return row["value"] if row else None


def delete_setting(chat_id: int, key: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM settings WHERE chat_id=? AND key=?",
            (chat_id, key),
        )


def log_action(chat_id: int, admin_id: int, target_id: int, action: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO action_log (chat_id, admin_id, target_id, action, created_at) VALUES (?,?,?,?,?)",
            (chat_id, admin_id, target_id, action, time.time()),
        )


def get_stats(chat_id: int) -> dict[str, Any]:
    with get_conn() as conn:
        total_messages = conn.execute(
            "SELECT COUNT(*) FROM action_log WHERE chat_id=?", (chat_id,)
        ).fetchone()[0]
        total_warnings = conn.execute(
            "SELECT COUNT(*) FROM warnings WHERE chat_id=?", (chat_id,)
        ).fetchone()[0]
        warned_members = conn.execute(
            "SELECT COUNT(DISTINCT user_id) FROM warnings WHERE chat_id=?", (chat_id,)
        ).fetchone()[0]
    return {
        "total_messages": total_messages,
        "total_warnings": total_warnings,
        "warned_members": warned_members,
    }
