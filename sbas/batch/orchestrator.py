"""
BatchOrchestrator — submits batches to LLM provider batch APIs and polls for results.
"""

import threading
import time
from typing import Dict, Any


class BatchOrchestrator:
    @staticmethod
    def submit_and_poll(batch: dict, results: dict, lock: threading.Lock):
        """
        Submits a batch of requests to LLM provider and polls until all results arrive.
        Falls back to individual sync calls if batch API is unavailable.
        """
        for job_id, req in batch.items():
            try:
                # Attempt batch API (provider-specific)
                # For MVP: fall back to direct sync call
                response = req["client"].chat.completions.create(
                    model=req["model"],
                    messages=req["messages"],
                    **req["kwargs"],
                )
                with lock:
                    results[job_id] = response
            except Exception as e:
                with lock:
                    results[job_id] = {"error": str(e)}
