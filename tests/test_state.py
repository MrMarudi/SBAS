"""Tests for state managers."""
import pytest
from sbas.state.memory import InMemoryStateManager


def test_save_and_load():
    sm = InMemoryStateManager()
    sm.save("job-1", {"messages": [{"role": "user", "content": "hello"}]})
    state = sm.load("job-1")
    assert state["messages"][0]["content"] == "hello"

def test_update():
    sm = InMemoryStateManager()
    sm.save("job-2", {"step": 1})
    sm.update("job-2", {"step": 2, "result": "done"})
    state = sm.load("job-2")
    assert state["step"] == 2
    assert state["result"] == "done"

def test_delete():
    sm = InMemoryStateManager()
    sm.save("job-3", {"data": "test"})
    sm.delete("job-3")
    assert sm.load("job-3") is None
