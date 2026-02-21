"""
SBASInterceptor — core LLM call interceptor.
Wraps any LLM client and transparently routes calls through the batch engine.
"""

from typing import Optional, Literal
from sbas.state.base import BaseStateManager
from sbas.state.memory import InMemoryStateManager
from sbas.batch.queue import BatchQueue
from sbas.cost.tracker import CostTracker
import time


LatencyBudget = Literal["realtime", "1h", "6h", "24h"]


class SBASInterceptor:
    """
    Drop-in wrapper for any LLM client.
    
    Usage:
        from sbas import SBAS
        from openai import OpenAI
        
        client = SBAS(OpenAI(), latency_budget="2h")
        # Use exactly like OpenAI client — costs 50% less
    """

    def __init__(
        self,
        llm_client,
        latency_budget: LatencyBudget = "1h",
        state_manager: Optional[BaseStateManager] = None,
        batch_queue: Optional[BatchQueue] = None,
        cost_tracker: Optional[CostTracker] = None,
        cloud_reporter=None,
    ):
        self._client = llm_client
        self.latency_budget = latency_budget
        self.state_manager = state_manager or InMemoryStateManager()
        self.batch_queue = batch_queue or BatchQueue()
        self.cost_tracker = cost_tracker or CostTracker()
        self.cloud_reporter = cloud_reporter
        self.chat = _ChatCompletionsProxy(self)

    def savings_report(self):
        return self.cost_tracker.report()

    def _should_use_async(self) -> bool:
        return self.latency_budget != "realtime"

    def _get_underlying_client(self):
        return self._client


class _ChatCompletionsProxy:
    def __init__(self, sbas: SBASInterceptor):
        self._sbas = sbas
        self.completions = _CompletionsProxy(sbas)


class _CompletionsProxy:
    def __init__(self, sbas: SBASInterceptor):
        self._sbas = sbas

    def create(self, model: str, messages: list, **kwargs):
        """
        Intercepts LLM call and routes to sync or async batch engine.
        """
        import uuid
        job_id = str(uuid.uuid4())
        start = time.time()

        if not self._sbas._should_use_async():
            # Direct sync call — no savings, no delay
            result = self._sbas._client.chat.completions.create(
                model=model, messages=messages, **kwargs
            )
            self._sbas.cost_tracker.record(job_id, result, mode="sync")
            return result

        # Async batch path
        # 1. Save current state
        state = {"messages": messages, "model": model, "kwargs": kwargs}
        self._sbas.state_manager.save(job_id, state)

        # 2. Enqueue for batch submission
        self._sbas.batch_queue.enqueue(
            job_id=job_id,
            model=model,
            messages=messages,
            kwargs=kwargs,
            client=self._sbas._client,
        )

        # 3. Return a pending job handle
        return PendingJob(job_id=job_id, sbas=self._sbas)


class PendingJob:
    """Represents an async batch job in progress."""
    
    def __init__(self, job_id: str, sbas: SBASInterceptor):
        self.job_id = job_id
        self._sbas = sbas
        self.status = "pending"

    def wait(self, poll_interval: int = 10, timeout: int = 86400):
        """Block until result is ready. Returns completion object."""
        import time
        elapsed = 0
        while elapsed < timeout:
            result = self._sbas.batch_queue.get_result(self.job_id)
            if result:
                self.status = "complete"
                self._sbas.state_manager.delete(self.job_id)
                self._sbas.cost_tracker.record(self.job_id, result, mode="async")
                return result
            time.sleep(poll_interval)
            elapsed += poll_interval
        raise TimeoutError(f"Job {self.job_id} did not complete within {timeout}s")

    def __repr__(self):
        return f"<PendingJob id={self.job_id} status={self.status}>"
