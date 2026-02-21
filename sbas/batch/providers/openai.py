"""
OpenAI Batch API adapter.
Uses /v1/batches endpoint for 50% cost reduction.
Docs: https://platform.openai.com/docs/guides/batch
"""

import json
import time
from typing import List, Dict, Any


class OpenAIBatchAdapter:
    def __init__(self, client):
        self._client = client

    def submit(self, requests: List[Dict]) -> str:
        """Submit a batch of requests. Returns batch_id."""
        # Build JSONL batch file
        lines = []
        for req in requests:
            lines.append(json.dumps({
                "custom_id": req["job_id"],
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": req["model"],
                    "messages": req["messages"],
                    **req.get("kwargs", {}),
                }
            }))
        
        jsonl_content = "\n".join(lines).encode()
        
        # Upload file
        file_obj = self._client.files.create(
            file=("batch.jsonl", jsonl_content, "application/jsonl"),
            purpose="batch",
        )
        
        # Create batch
        batch = self._client.batches.create(
            input_file_id=file_obj.id,
            endpoint="/v1/chat/completions",
            completion_window="24h",
        )
        return batch.id

    def poll(self, batch_id: str, poll_interval: int = 30) -> Dict[str, Any]:
        """Poll until batch is complete. Returns dict of job_id -> response."""
        while True:
            batch = self._client.batches.retrieve(batch_id)
            if batch.status == "completed":
                return self._parse_results(batch.output_file_id)
            elif batch.status in ("failed", "cancelled", "expired"):
                raise RuntimeError(f"Batch {batch_id} failed with status: {batch.status}")
            time.sleep(poll_interval)

    def _parse_results(self, output_file_id: str) -> Dict[str, Any]:
        content = self._client.files.content(output_file_id).text
        results = {}
        for line in content.strip().split("\n"):
            item = json.loads(line)
            results[item["custom_id"]] = item["response"]["body"]
        return results
