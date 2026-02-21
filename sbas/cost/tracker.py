"""
CostTracker — measures actual vs potential savings per LLM call.
"""

import time
from typing import Any, Optional
from dataclasses import dataclass, field


# Approximate cost per 1M tokens (input + output average) — update as providers change
COST_TABLE = {
    "gpt-4o": {"sync": 7.50, "async": 3.75},
    "gpt-4o-mini": {"sync": 0.30, "async": 0.15},
    "gpt-3.5-turbo": {"sync": 0.50, "async": 0.25},
    "claude-3-5-sonnet-20241022": {"sync": 3.00, "async": 1.50},
    "claude-3-5-haiku-20241022": {"sync": 0.80, "async": 0.40},
}


@dataclass
class CostRecord:
    job_id: str
    model: str
    tokens_in: int
    tokens_out: int
    mode: str  # "sync" | "async"
    cost_actual: float
    cost_if_sync: float
    saved: float
    timestamp: float = field(default_factory=time.time)


class CostTracker:
    def __init__(self):
        self._records = []

    def record(self, job_id: str, response: Any, mode: str) -> None:
        try:
            model = getattr(response, "model", "unknown")
            usage = getattr(response, "usage", None)
            tokens_in = getattr(usage, "prompt_tokens", 0) if usage else 0
            tokens_out = getattr(usage, "completion_tokens", 0) if usage else 0
            
            rates = COST_TABLE.get(model, {"sync": 5.0, "async": 2.5})
            total_tokens = (tokens_in + tokens_out) / 1_000_000
            
            cost_actual = total_tokens * rates.get(mode, rates["sync"])
            cost_if_sync = total_tokens * rates["sync"]
            saved = cost_if_sync - cost_actual if mode == "async" else 0

            self._records.append(CostRecord(
                job_id=job_id,
                model=model,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                mode=mode,
                cost_actual=cost_actual,
                cost_if_sync=cost_if_sync,
                saved=saved,
            ))
        except Exception:
            pass  # Never let tracking break the main flow

    def report(self, since: Optional[float] = None) -> dict:
        records = self._records
        if since:
            records = [r for r in records if r.timestamp >= since]
        
        total_actual = sum(r.cost_actual for r in records)
        total_if_sync = sum(r.cost_if_sync for r in records)
        total_saved = sum(r.saved for r in records)
        sync_calls = sum(1 for r in records if r.mode == "sync")
        async_calls = sum(1 for r in records if r.mode == "async")
        pct = round((total_saved / total_if_sync * 100) if total_if_sync > 0 else 0, 1)

        return {
            "total_calls": len(records),
            "sync_calls": sync_calls,
            "async_calls": async_calls,
            "total_cost": round(total_actual, 4),
            "cost_if_all_sync": round(total_if_sync, 4),
            "total_saved": round(total_saved, 4),
            "savings_pct": pct,
            "projected_monthly": round(total_saved * 30, 2),
        }
