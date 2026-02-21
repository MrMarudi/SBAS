"""Tests for cost tracker."""
from sbas.cost.tracker import CostTracker


class MockUsage:
    prompt_tokens = 500
    completion_tokens = 200


class MockResponse:
    model = "gpt-4o"
    usage = MockUsage()


def test_report_empty():
    ct = CostTracker()
    report = ct.report()
    assert report["total_calls"] == 0
    assert report["total_saved"] == 0.0

def test_async_saves_money():
    ct = CostTracker()
    ct.record("job-1", MockResponse(), mode="async")
    report = ct.report()
    assert report["async_calls"] == 1
    assert report["total_saved"] > 0
    assert report["savings_pct"] > 0
