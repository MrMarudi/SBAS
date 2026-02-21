"""
SBAS Demo: Checkout Analysis Agent
From the patent — simulates a user journey to checkout page and analyzes PayPal presentation.
"""

from sbas import SBAS, SQLiteStateManager
from openai import OpenAI
import os


def run_checkout_agent():
    # 1. Wrap your existing OpenAI client — one line change
    client = SBAS(
        OpenAI(api_key=os.environ["OPENAI_API_KEY"]),
        latency_budget="2h",                            # can wait up to 2 hours
        state_manager=SQLiteStateManager("./demo.db"),  # state saved locally
    )

    # 2. Simulate checkout analysis — works exactly like OpenAI
    steps = [
        "You are a checkout analysis agent. Step 1: Navigate to product page. Describe what you see.",
        "Step 2: Add item to cart. Confirm cart contents.",
        "Step 3: Proceed to checkout. Analyze all payment options shown.",
        "Step 4: Focus on PayPal presentation. Rate visibility from 1-10 and explain.",
    ]

    messages = [{"role": "system", "content": "You are an e-commerce analysis agent."}]

    for step in steps:
        messages.append({"role": "user", "content": step})
        
        job = client.chat.completions.create(model="gpt-4o", messages=messages)
        
        if hasattr(job, "wait"):
            print(f"⏳ Async job submitted: {job.job_id}")
            result = job.wait()  # waits for batch result
        else:
            result = job
        
        assistant_msg = result.choices[0].message.content
        messages.append({"role": "assistant", "content": assistant_msg})
        print(f"✅ {step[:50]}...\n→ {assistant_msg[:100]}...\n")

    # 3. See how much you saved
    print("\n💰 Savings Report:")
    report = client.savings_report()
    for k, v in report.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    run_checkout_agent()
