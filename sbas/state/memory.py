"""In-memory state manager. Use for dev/testing only — state lost on restart."""

from sbas.state.base import BaseStateManager
from typing import Optional


class InMemoryStateManager(BaseStateManager):
    def __init__(self):
        self._store = {}

    def save(self, job_id: str, state: dict) -> None:
        self._store[job_id] = state.copy()

    def load(self, job_id: str) -> Optional[dict]:
        return self._store.get(job_id)

    def update(self, job_id: str, delta: dict) -> None:
        if job_id in self._store:
            self._store[job_id].update(delta)

    def delete(self, job_id: str) -> None:
        self._store.pop(job_id, None)
