"""
BatchQueue — collects LLM requests and groups them for batch submission.
"""

from typing import Optional, Dict, Any
import threading


class BatchQueue:
    def __init__(self, max_size: int = 100, max_wait_sec: int = 300):
        self._queue = {}       # job_id -> request
        self._results = {}     # job_id -> response
        self._lock = threading.Lock()
        self.max_size = max_size
        self.max_wait_sec = max_wait_sec

    def enqueue(self, job_id: str, model: str, messages: list, kwargs: dict, client) -> None:
        with self._lock:
            self._queue[job_id] = {
                "model": model,
                "messages": messages,
                "kwargs": kwargs,
                "client": client,
            }
        # Auto-submit if batch is full
        if len(self._queue) >= self.max_size:
            self._submit_batch()

    def get_result(self, job_id: str) -> Optional[Any]:
        with self._lock:
            return self._results.pop(job_id, None)

    def _submit_batch(self):
        """Submit current queue as a batch to LLM provider."""
        from sbas.batch.orchestrator import BatchOrchestrator
        with self._lock:
            if not self._queue:
                return
            batch = dict(self._queue)
            self._queue.clear()
        
        # Submit in background thread
        thread = threading.Thread(
            target=BatchOrchestrator.submit_and_poll,
            args=(batch, self._results, self._lock),
            daemon=True,
        )
        thread.start()
