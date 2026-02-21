# SBAS — Sequential Batch Agent System

> Run AI agents at **50% lower cost** using async batch LLM APIs — without changing your workflow.

## How it works

SBAS is a **drop-in SDK** that runs entirely inside your infrastructure.  
Your data never leaves your servers. Your API keys stay with you.  
We handle the orchestration logic. You keep control.

```python
# Before SBAS
from langchain.llms import OpenAI
llm = OpenAI()

# After SBAS — one line change
from sbas import SBAS
llm = SBAS(OpenAI(), latency_budget="2h")
```

That's it. Everything else works exactly as before — but costs half as much.

---

## Architecture

```
Your Server
┌─────────────────────────────────────────────────────┐
│                                                     │
│   Your Agent Code                                   │
│        │                                            │
│   SBAS SDK                                          │
│   ├── Interceptor     ← wraps your LLM client       │
│   ├── State Manager   ← saves/restores agent state  │
│   ├── Batch Queue     ← groups requests             │
│   └── Cost Tracker    ← measures savings            │
│        │                                            │
│        └──→ Direct call to OpenAI / Anthropic       │
│             (your API key, your data, your call)    │
└─────────────────────────────────────────────────────┘
         │
         │  Metadata only (no prompts, no data)
         ▼
SBAS Cloud Dashboard (optional)
├── Job status & history
├── Cost savings report
├── Team analytics
└── Alerts & monitoring
```

**What SBAS cloud sees:** job IDs, timing, token counts, cost metrics  
**What SBAS cloud never sees:** prompts, responses, API keys, business data

---

## Core Components

### 1. Interceptor
Wraps any LLM client and transparently routes calls through the batch engine.  
Supports: OpenAI, Anthropic, LangChain, LangGraph, CrewAI, AutoGen.

### 2. State Manager
Captures the full agent state after every step.  
When an async response arrives, reconstructs the session and resumes exactly where it left off.  
Storage: local Redis, SQLite, or your own DB — your choice.

### 3. Batch Orchestrator
Groups pending LLM calls across agents into optimal batch sizes.  
Submits to provider batch API. Polls for results. Maps responses back to the correct agent/task.

### 4. Cost Tracker
Real-time measurement of sync vs async cost per run.  
Outputs savings report per job, per agent, per day.

---

## Latency Budgets

Not every task tolerates delay. SBAS lets you configure per-agent:

```python
# Time-sensitive: use sync (no savings, no delay)
llm = SBAS(OpenAI(), latency_budget="realtime")

# Can wait an hour: mix of sync + async
llm = SBAS(OpenAI(), latency_budget="1h")

# Batch overnight jobs: full async (max savings)
llm = SBAS(OpenAI(), latency_budget="24h")
```

---

## Supported Integrations

| Framework     | Status     |
|---------------|------------|
| OpenAI SDK    | ✅ v1      |
| Anthropic SDK | ✅ v1      |
| LangChain     | ✅ v1      |
| LangGraph     | 🔜 v1.1    |
| CrewAI        | 🔜 v1.1    |
| AutoGen       | 🔜 v2      |

---

## Installation

```bash
pip install sbas
```

---

## Quick Start

```python
from sbas import SBAS
from sbas.state import RedisStateManager
from openai import OpenAI

# 1. Wrap your existing LLM client
client = SBAS(
    OpenAI(api_key="your-key"),         # your key, stays on your server
    latency_budget="2h",                # how long can this task wait?
    state_manager=RedisStateManager(),  # where to store agent state
)

# 2. Use exactly as before
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Analyze this invoice..."}]
)

# 3. Check savings
print(client.savings_report())
# → Saved $0.43 this run (51% reduction)
```

---

## Security

- 🔑 API keys never leave your environment
- 🏠 Prompts and responses stay on your servers
- 📊 Only anonymized metadata sent to SBAS cloud (optional)
- 🏢 Full on-prem deployment available for enterprise

---

## Roadmap

- [ ] v1.0 — Core SDK (interceptor + state manager + batch orchestrator)
- [ ] v1.1 — LangGraph + CrewAI integrations
- [ ] v1.2 — Web dashboard (cloud)
- [ ] v2.0 — AutoGen + on-prem enterprise package

---

## License

MIT (core SDK) — Commercial license for enterprise features.

---

*Built by Lior Nataf & Matan Marudi · Patent pending 2025*
