"""
Anthropic Batch API adapter.
Uses /v1/messages/batches endpoint for 50% cost reduction.
Docs: https://docs.anthropic.com/en/docs/build-with-claude/message-batches
"""

import time
from typing import List, Dict, Any


class AnthropicBatchAdapter:
    def __init__(self, client):
        self._client = client

    def submit(self, requests: List[Dict]) -> str:
        """Submit a batch of requests. Returns batch_id."""
        batch_requests = []
        for req in requests:
            batch_requests.append({
                "custom_id": req["job_id"],
                "params": {
                    "model": req["model"],
                    "messages": req["messages"],
                    "max_tokens": req.get("kwargs", {}).get("max_tokens", 1024),
                }
            })
        
        batch = self._client.messages.batches.create(requests=batch_requests)
        return batch.id

    def poll(self, batch_id: str, poll_interval: int = 30) -> Dict[str, Any]:
        """Poll until batch is complete. Returns dict of job_id -> response."""
        while True:
            batch = self._client.messages.batches.retrieve(batch_id)
            if batch.processing_status == "ended":
                return self._parse_results(batch_id)
            time.sleep(poll_interval)

    def _parse_results(self, batch_id: str) -> Dict[str, Any]:
        results = {}
        for result in self._client.messages.batches.results(batch_id):
            if result.result.type == "succeeded":
                results[result.custom_id] = result.result.message
        return results
