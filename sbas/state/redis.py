"""Redis-backed state manager. Recommended for production."""

import json
from sbas.state.base import BaseStateManager
from typing import Optional


class RedisStateManager(BaseStateManager):
    def __init__(self, url: str = "redis://localhost:6379", ttl: int = 86400 * 7):
        try:
            import redis
            self._r = redis.from_url(url)
            self._ttl = ttl  # default 7 days
        except ImportError:
            raise ImportError("Install redis: pip install redis")

    def _key(self, job_id: str) -> str:
        return f"sbas:state:{job_id}"

    def save(self, job_id: str, state: dict) -> None:
        self._r.setex(self._key(job_id), self._ttl, json.dumps(state))

    def load(self, job_id: str) -> Optional[dict]:
        val = self._r.get(self._key(job_id))
        return json.loads(val) if val else None

    def update(self, job_id: str, delta: dict) -> None:
        state = self.load(job_id) or {}
        state.update(delta)
        self.save(job_id, state)

    def delete(self, job_id: str) -> None:
        self._r.delete(self._key(job_id))
