import pytest

from src.utils.cost_control import DailyBudgetExceeded, DailyRequestBudget, JsonResponseCache


def test_daily_request_budget_blocks_after_limit(tmp_path):
    budget = DailyRequestBudget("x_test", daily_limit=1, state_dir=tmp_path)
    budget.consume()
    assert budget.remaining() == 0
    with pytest.raises(DailyBudgetExceeded):
        budget.consume()


def test_json_response_cache_roundtrip(tmp_path):
    cache = JsonResponseCache(tmp_path)
    key = {"query": "AI", "max_pages": 1}
    pages = [{"data": [{"id": "1"}]}]
    cache.save("x", key, pages)
    assert cache.load("x", key, ttl_minutes=60) == pages
    assert cache.load("x", key, ttl_minutes=0) is None
