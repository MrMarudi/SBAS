# SBAS — Technical Architecture Spec

## Overview

SBAS is designed as a **SDK-first, data-private** system.  
The core principle: all sensitive data (prompts, responses, API keys) stays inside the user's infrastructure.  
SBAS cloud only receives anonymized metadata for analytics and dashboard purposes.

---

## Component Deep Dive

---

### Component 1: Interceptor

**Purpose:** Wraps any LLM client transparently. The developer changes one line of code.

**Interface:**
```python
class SBASInterceptor:
    def __init__(self, llm_client, latency_budget, state_manager, batch_queue):
        ...
    
    def chat.completions.create(self, model, messages, **kwargs):
        # 1. Check latency_budget → decide sync or async route
        # 2. If async → save state, submit to BatchQueue, return job_id
        # 3. If sync → pass directly to underlying llm_client
        ...
```

**Routing Logic:**
```
latency_budget = "realtime"  → always sync (bypass SBAS, direct LLM call)
latency_budget = "1h"        → async if batch window available, sync as fallback
latency_budget = "24h"       → always async (maximum savings)
```

**Provider Adapters (one per provider):**
- `adapters/openai.py` — wraps `openai.OpenAI()`
- `adapters/anthropic.py` — wraps `anthropic.Anthropic()`
- `adapters/langchain.py` — wraps any LangChain LLM/ChatModel
- `adapters/langgraph.py` — hooks into LangGraph node execution

---

### Component 2: State Manager

**Purpose:** Saves the complete agent state after every step so it can be reconstructed when an async response arrives.

**What "state" means:**
- Conversation history (messages array)
- Current step in the workflow
- Variables and context in scope
- Pending tool calls / results
- Session metadata (agent ID, job ID, timestamp)

**Interface:**
```python
class StateManager:
    def save(self, job_id: str, state: AgentState) -> None: ...
    def load(self, job_id: str) -> AgentState: ...
    def update(self, job_id: str, delta: dict) -> None: ...
    def delete(self, job_id: str) -> None: ...
```

**Storage Backends (pluggable):**
```python
RedisStateManager(url="redis://localhost:6379")   # recommended for production
SQLiteStateManager(path="./sbas_state.db")        # zero-dependency option
InMemoryStateManager()                             # testing/dev only
CustomStateManager(your_db_connection)             # bring your own
```

**State Reconstruction Flow:**
```
1. Async response arrives
2. Load state from store using job_id
3. Inject LLM response into state.messages
4. Resume agent execution from saved checkpoint
5. Continue to next step or complete job
```

---

### Component 3: Batch Orchestrator

**Purpose:** Collects pending LLM requests, groups them into optimal batches, submits to provider batch API, and routes responses back to the correct agent.

**Flow:**
```
Agent A ──→ BatchQueue.enqueue(request_A, job_id_A)
Agent B ──→ BatchQueue.enqueue(request_B, job_id_B)
Agent C ──→ BatchQueue.enqueue(request_C, job_id_C)
              │
              ▼ (batch window: configurable, e.g. every 100 requests or 5 min)
         BatchOrchestrator.submit_batch([A, B, C])
              │
              ▼
         OpenAI Batch API / Anthropic Batch API
              │
              ▼ (async, minutes to hours later)
         BatchOrchestrator.poll_results()
              │
              ├──→ Response A → StateManager.update(job_id_A) → Resume Agent A
              ├──→ Response B → StateManager.update(job_id_B) → Resume Agent B
              └──→ Response C → StateManager.update(job_id_C) → Resume Agent C
```

**BatchQueue interface:**
```python
class BatchQueue:
    def enqueue(self, request: LLMRequest, job_id: str) -> None: ...
    def flush(self) -> List[LLMRequest]: ...          # submit current batch
    def auto_flush_policy(self, max_size=100, max_wait_sec=300): ...
```

**Provider Batch Adapters:**
```python
OpenAIBatchAdapter   → uses /v1/batches endpoint
AnthropicBatchAdapter → uses /v1/messages/batches endpoint
```

---

### Component 4: Cost Tracker

**Purpose:** Measures actual cost of each LLM call (sync vs what async would have cost) and reports savings.

**Interface:**
```python
class CostTracker:
    def record(self, job_id, tokens_in, tokens_out, mode: "sync"|"async"): ...
    def savings_report(self, job_id=None, since=None) -> SavingsReport: ...
```

**Output:**
```
SavingsReport:
  period: last 24h
  sync_calls: 42  →  cost: $8.40
  async_calls: 318 →  cost: $3.18
  total_saved: $5.22  (47% reduction)
  projected_monthly: $156 saved
```

---

## Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│  USER INFRASTRUCTURE (nothing leaves this boundary)              │
│                                                                  │
│  Agent Code                                                      │
│     │                                                            │
│  SBASInterceptor                                                 │
│     ├── sync path ──────────────────────────────────────────┐   │
│     │                                                        │   │
│     └── async path                                          │   │
│          │                                                   │   │
│          ├── StateManager.save(state)                        │   │
│          │                                                   │   │
│          └── BatchQueue.enqueue(request)                     │   │
│                    │                                         │   │
│               BatchOrchestrator                              │   │
│                    │                                         │   │
│                    ▼                                         ▼   │
│             LLM Provider API ←──────────────────────────────┘   │
│          (OpenAI / Anthropic)                                    │
│                    │                                            │
│                    ▼                                            │
│             BatchOrchestrator.poll()                            │
│                    │                                            │
│             StateManager.update()                               │
│                    │                                            │
│             Agent resumes ✓                                     │
│                                                                  │
│  CostTracker ──→ local savings log                              │
│       │                                                         │
│       └──→ (optional) anonymized metrics → SBAS Cloud          │
│                        [job_id, token_count, savings %]         │
│                        [NO prompts, NO responses, NO keys]      │
└──────────────────────────────────────────────────────────────────┘
```

---

## Failure Handling

| Failure | Response |
|---------|----------|
| Async job times out | Auto-retry with sync fallback |
| State store unavailable | In-memory fallback + alert |
| Batch API error | Requeue individual requests |
| Agent crash mid-job | Resume from last saved checkpoint |
| Network loss | Local queue persists, retry on reconnect |

---

## Security Model

| Data Type | Where it lives | SBAS cloud sees it? |
|-----------|---------------|---------------------|
| LLM API keys | User's env vars | ❌ Never |
| Prompts / messages | User's server | ❌ Never |
| LLM responses | User's server | ❌ Never |
| Agent state | User's state store | ❌ Never |
| Job ID | Both | ✅ Yes |
| Token counts | Both | ✅ Yes (anonymized) |
| Cost savings % | Both | ✅ Yes (anonymized) |
| Timing metrics | Both | ✅ Yes (anonymized) |

---

## File Structure

```
sbas/
├── __init__.py              # main SBAS() entry point
├── interceptor.py           # core LLM call interceptor
├── state/
│   ├── __init__.py
│   ├── base.py              # StateManager abstract class
│   ├── redis.py             # RedisStateManager
│   ├── sqlite.py            # SQLiteStateManager
│   └── memory.py            # InMemoryStateManager
├── batch/
│   ├── __init__.py
│   ├── queue.py             # BatchQueue
│   ├── orchestrator.py      # BatchOrchestrator
│   └── providers/
│       ├── openai.py        # OpenAI Batch API adapter
│       └── anthropic.py     # Anthropic Batch API adapter
├── adapters/
│   ├── openai.py            # OpenAI client adapter
│   ├── anthropic.py         # Anthropic client adapter
│   ├── langchain.py         # LangChain adapter
│   └── langgraph.py         # LangGraph adapter
├── cost/
│   ├── tracker.py           # CostTracker
│   └── report.py            # SavingsReport
└── cloud/
    └── reporter.py          # Optional: sends anonymized metrics to SBAS cloud
```

---

## MVP Checklist (Week 1-6)

- [ ] `interceptor.py` — core routing logic
- [ ] `state/memory.py` — in-memory state (dev/test)
- [ ] `state/redis.py` — production state manager
- [ ] `batch/queue.py` — batch collection
- [ ] `batch/providers/openai.py` — OpenAI batch adapter
- [ ] `batch/providers/anthropic.py` — Anthropic batch adapter
- [ ] `adapters/openai.py` — OpenAI client wrapper
- [ ] `adapters/langchain.py` — LangChain wrapper
- [ ] `cost/tracker.py` — savings measurement
- [ ] `examples/checkout_agent.py` — demo from patent
- [ ] `tests/` — unit tests for all components
- [ ] PyPI publish

---

*Patent pending 2025 · Lior Nataf & Matan Marudi*
