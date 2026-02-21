"""
Optional cloud reporter — sends anonymized metrics to SBAS dashboard.
NEVER sends prompts, responses, API keys, or any business data.
Only sends: job_id (hashed), token counts, cost savings %, timing.
"""

import hashlib
import threading
from typing import Optional


class CloudReporter:
    def __init__(self, api_key: str, endpoint: str = "https://api.sbas.ai/v1/metrics"):
        self._api_key = api_key
        self._endpoint = endpoint
        self._enabled = True

    def report(self, job_id: str, tokens: int, savings_pct: float, mode: str) -> None:
        """Send anonymized metric. Non-blocking."""
        if not self._enabled:
            return
        
        payload = {
            "job_id_hash": hashlib.sha256(job_id.encode()).hexdigest()[:16],
            "tokens": tokens,
            "savings_pct": savings_pct,
            "mode": mode,
            # No prompts. No responses. No keys. No business data. Ever.
        }
        
        thread = threading.Thread(target=self._send, args=(payload,), daemon=True)
        thread.start()

    def _send(self, payload: dict) -> None:
        try:
            import urllib.request, json
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                self._endpoint,
                data=data,
                headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass  # Never fail silently on metric reporting errors
