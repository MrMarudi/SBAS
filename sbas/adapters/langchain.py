"""
LangChain adapter for SBAS.
Wraps any LangChain LLM or ChatModel.

Usage:
    from langchain_openai import ChatOpenAI
    from sbas.adapters.langchain import SBASLangChain
    
    llm = SBASLangChain(ChatOpenAI(), latency_budget="2h")
    result = llm.invoke("Analyze this document...")
"""

from sbas.interceptor import SBASInterceptor
from typing import Optional


class SBASLangChain:
    def __init__(self, llm, latency_budget="1h", state_manager=None):
        self._llm = llm
        self._sbas = SBASInterceptor(
            llm_client=llm,
            latency_budget=latency_budget,
            state_manager=state_manager,
        )

    def invoke(self, input, config=None, **kwargs):
        # For realtime budget, pass through directly
        if self._sbas.latency_budget == "realtime":
            return self._llm.invoke(input, config=config, **kwargs)
        # Otherwise route through SBAS batch engine
        return self._llm.invoke(input, config=config, **kwargs)  # MVP: extend in v1.1

    def savings_report(self):
        return self._sbas.savings_report()
