"""SQLite-backed state manager. Zero-dependency option for production."""

import json
import sqlite3
from sbas.state.base import BaseStateManager
from typing import Optional


class SQLiteStateManager(BaseStateManager):
    def __init__(self, path: str = "./sbas_state.db"):
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS sbas_state (job_id TEXT PRIMARY KEY, state TEXT, updated_at REAL)"
        )
        self._conn.commit()

    def save(self, job_id: str, state: dict) -> None:
        import time
        self._conn.execute(
            "INSERT OR REPLACE INTO sbas_state VALUES (?, ?, ?)",
            (job_id, json.dumps(state), time.time()),
        )
        self._conn.commit()

    def load(self, job_id: str) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT state FROM sbas_state WHERE job_id = ?", (job_id,)
        ).fetchone()
        return json.loads(row[0]) if row else None

    def update(self, job_id: str, delta: dict) -> None:
        state = self.load(job_id) or {}
        state.update(delta)
        self.save(job_id, state)

    def delete(self, job_id: str) -> None:
        self._conn.execute("DELETE FROM sbas_state WHERE job_id = ?", (job_id,))
        self._conn.commit()
