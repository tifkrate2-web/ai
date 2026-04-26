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
            CREATE TABLE IF NOT EXISTS messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id     INTEGER NOT NULL,
                user_id     INTEGER NOT NULL,
                role        TEXT    NOT NULL,  -- 'user' | 'assistant'
                content     TEXT    NOT NULL,
                created_at  REAL    NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_messages_chat
                ON messages (chat_id, created_at);

            CREATE TABLE IF NOT EXISTS rate_limits (
                user_id     INTEGER NOT NULL,
                chat_id     INTEGER NOT NULL,
                ts          REAL    NOT NULL,
                PRIMARY KEY (user_id, chat_id, ts)
            );

            CREATE TABLE IF NOT EXISTS stats (
                chat_id         INTEGER PRIMARY KEY,
                total_messages  INTEGER NOT NULL DEFAULT 0,
                last_active     REAL    NOT NULL DEFAULT 0
            );
        """)


def add_message(chat_id: int, user_id: int, role: str, content: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO messages (chat_id, user_id, role, content, created_at) VALUES (?,?,?,?,?)",
            (chat_id, user_id, role, content, time.time()),
        )
        conn.execute(
            """INSERT INTO stats (chat_id, total_messages, last_active)
               VALUES (?, 1, ?)
               ON CONFLICT(chat_id) DO UPDATE SET
                   total_messages = total_messages + 1,
                   last_active = excluded.last_active""",
            (chat_id, time.time()),
        )


def get_history(chat_id: int, limit: int = 20) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT role, content FROM messages
               WHERE chat_id = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (chat_id, limit),
        ).fetchall()
    # Return in chronological order
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def clear_history(chat_id: int) -> int:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        return cur.rowcount


def get_stats(chat_id: int) -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT total_messages, last_active FROM stats WHERE chat_id = ?",
            (chat_id,),
        ).fetchone()
    if row is None:
        return {"total_messages": 0, "last_active": None}
    return {"total_messages": row["total_messages"], "last_active": row["last_active"]}


def check_rate_limit(user_id: int, chat_id: int, max_per_min: int) -> bool:
    """Return True if the user is within the rate limit, False if exceeded."""
    now = time.time()
    window_start = now - 60
    with get_conn() as conn:
        # Remove old entries
        conn.execute(
            "DELETE FROM rate_limits WHERE user_id=? AND chat_id=? AND ts<?",
            (user_id, chat_id, window_start),
        )
        count = conn.execute(
            "SELECT COUNT(*) FROM rate_limits WHERE user_id=? AND chat_id=? AND ts>=?",
            (user_id, chat_id, window_start),
        ).fetchone()[0]
        if count >= max_per_min:
            return False
        conn.execute(
            "INSERT OR IGNORE INTO rate_limits (user_id, chat_id, ts) VALUES (?,?,?)",
            (user_id, chat_id, now),
        )
    return True
